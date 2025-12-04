import os
import logging
from msal import ConfidentialClientApplication
import aiohttp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SharePointService:
    def __init__(self):
        self.client_id = os.environ.get('AZURE_CLIENT_ID')
        self.client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        self.tenant_id = os.environ.get('AZURE_TENANT_ID')
        self.site_url = os.environ.get('SHAREPOINT_SITE_URL', 'https://abscolorado365.sharepoint.com/sites/PMs')
        self.token = None
        
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            logger.warning("SharePoint credentials not fully configured")
    
    async def _get_access_token(self) -> str:
        """Get Microsoft Graph API access token"""
        if self.token:
            return self.token
        
        try:
            app = ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                self.token = result["access_token"]
                return self.token
            else:
                error = result.get("error", "Unknown error")
                error_desc = result.get("error_description", "No description")
                raise Exception(f"Token acquisition failed: {error} - {error_desc}")
        
        except Exception as e:
            logger.error(f"Failed to get access token: {str(e)}")
            raise
    
    async def upload_pdf(self, filename: str, content: bytes, folder_path: str) -> str:
        """Upload a PDF to SharePoint
        
        Args:
            filename: Name of the PDF file
            content: PDF file content as bytes
            folder_path: SharePoint folder path (relative to site)
        
        Returns:
            SharePoint file ID
        """
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            logger.warning(f"SharePoint not configured - simulating upload of {filename}")
            return f"mock_id_{filename}"
        
        try:
            token = await self._get_access_token()
            
            # Parse site URL
            site_domain = self.site_url.split('/sites/')[0].replace('https://', '')
            site_path = self.site_url.split('/sites/')[1] if '/sites/' in self.site_url else ''
            
            # Get site ID
            site_id = await self._get_site_id(token, site_domain, site_path)
            
            # Get drive ID
            drive_id = await self._get_drive_id(token, site_id)
            
            # Create folder path if it doesn't exist
            folder_id = await self._ensure_folder_exists(token, site_id, drive_id, folder_path)
            
            # Upload file
            file_id = await self._upload_file(token, site_id, drive_id, folder_id, filename, content)
            
            logger.info(f"Successfully uploaded {filename} to SharePoint")
            return file_id
        
        except Exception as e:
            logger.error(f"Failed to upload {filename} to SharePoint: {str(e)}")
            raise
    
    async def _get_site_id(self, token: str, domain: str, site_path: str) -> str:
        """Get SharePoint site ID"""
        async with aiohttp.ClientSession() as session:
            url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_path}"
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['id']
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get site ID: {response.status} - {error_text}")
    
    async def _get_drive_id(self, token: str, site_id: str) -> str:
        """Get default document library (drive) ID for the site"""
        async with aiohttp.ClientSession() as session:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['id']
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get drive ID: {response.status} - {error_text}")
    
    async def _ensure_folder_exists(self, token: str, site_id: str, drive_id: str, folder_path: str) -> str:
        """Ensure folder path exists, create if needed, and return folder ID"""
        # Clean up folder path
        folder_path = folder_path.strip('/')
        
        if not folder_path:
            return "root"
        
        # Split path into parts
        path_parts = [p.strip() for p in folder_path.split('/') if p.strip()]
        
        current_parent_id = "root"
        
        # Navigate/create each folder in the path
        for folder_name in path_parts:
            try:
                # Try to get the folder first
                async with aiohttp.ClientSession() as session:
                    # Search for folder by name under current parent
                    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{current_parent_id}/children"
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Look for existing folder
                            folder_found = False
                            for item in data.get('value', []):
                                if item.get('name') == folder_name and 'folder' in item:
                                    current_parent_id = item['id']
                                    folder_found = True
                                    logger.info(f"Found existing folder: {folder_name}")
                                    break
                            
                            # Create folder if not found
                            if not folder_found:
                                create_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{current_parent_id}/children"
                                create_data = {
                                    "name": folder_name,
                                    "folder": {},
                                    "@microsoft.graph.conflictBehavior": "rename"
                                }
                                headers["Content-Type"] = "application/json"
                                
                                async with session.post(create_url, json=create_data, headers=headers) as create_response:
                                    if create_response.status in [200, 201]:
                                        folder_data = await create_response.json()
                                        current_parent_id = folder_data['id']
                                        logger.info(f"Created new folder: {folder_name}")
                                    else:
                                        error_text = await create_response.text()
                                        logger.error(f"Failed to create folder {folder_name}: {error_text}")
                                        # Continue with current parent if folder creation fails
                        else:
                            error_text = await response.text()
                            logger.error(f"Failed to list folder contents: {error_text}")
            
            except Exception as e:
                logger.error(f"Error ensuring folder exists for {folder_name}: {str(e)}")
                # Continue with current parent on error
        
        return current_parent_id
    
    async def _upload_file(self, token: str, site_id: str, drive_id: str, folder_id: str, filename: str, content: bytes) -> str:
        """Upload file to SharePoint"""
        async with aiohttp.ClientSession() as session:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}:/{filename}:/content"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/pdf"
            }
            
            async with session.put(url, data=content, headers=headers) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return data['id']
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to upload file: {response.status} - {error_text}")