import requests
import sys
import json
import os
from datetime import datetime

class DocumentIngestionTester:
    def __init__(self, base_url="https://github-contract-add.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.contract_file_ids = []
        self.proposal_file_ids = []
        self.test_results = []

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = f"{status} - {test_name}"
        if details:
            result += f"\n   Details: {details}"
        
        print(result)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        return passed

    def test_health_check(self):
        """Test health endpoint"""
        print("\n🔍 Testing Health Check...")
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            passed = response.status_code == 200 and response.json().get("status") == "healthy"
            return self.log_result(
                "Health Check",
                passed,
                f"Status: {response.status_code}, Response: {response.json()}"
            )
        except Exception as e:
            return self.log_result("Health Check", False, str(e))

    def test_list_documents_empty(self):
        """Test listing documents when empty"""
        print("\n🔍 Testing List Documents (Initial)...")
        try:
            response = requests.get(f"{self.base_url}/api/documents", timeout=10)
            if response.status_code == 200:
                data = response.json()
                passed = isinstance(data, list)
                return self.log_result(
                    "List Documents (Initial)",
                    passed,
                    f"Retrieved {len(data)} documents"
                )
            else:
                return self.log_result(
                    "List Documents (Initial)",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("List Documents (Initial)", False, str(e))

    def test_upload_contract(self):
        """Test uploading a contract document"""
        print("\n🔍 Testing Contract Upload...")
        try:
            # Check if test file exists
            test_file = '/app/test_contract.pdf'
            if not os.path.exists(test_file):
                test_file = '/app/test_contract.docx'
            
            if not os.path.exists(test_file):
                return self.log_result("Contract Upload", False, "No test contract file found")
            
            with open(test_file, 'rb') as f:
                files = {'file': (os.path.basename(test_file), f, 'application/pdf' if test_file.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                response = requests.post(
                    f"{self.base_url}/api/upload?document_type=contract",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                file_id = data.get('file_id')
                self.contract_file_ids.append(file_id)
                
                # Verify response structure
                expected_fields = ['file_id', 'filename', 'document_type', 'is_active', 'upload_date']
                has_all_fields = all(field in data for field in expected_fields)
                correct_type = data.get('document_type') == 'contract'
                is_active = data.get('is_active') == True
                
                passed = file_id and has_all_fields and correct_type and is_active
                return self.log_result(
                    "Contract Upload",
                    passed,
                    f"File ID: {file_id}, Type: {data.get('document_type')}, Active: {data.get('is_active')}"
                )
            else:
                return self.log_result(
                    "Contract Upload",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Contract Upload", False, str(e))

    def test_upload_proposal(self):
        """Test uploading a proposal document"""
        print("\n🔍 Testing Proposal Upload...")
        try:
            # Use same test file but as proposal
            test_file = '/app/test_contract.pdf'
            if not os.path.exists(test_file):
                test_file = '/app/test_contract.docx'
            
            if not os.path.exists(test_file):
                return self.log_result("Proposal Upload", False, "No test file found")
            
            with open(test_file, 'rb') as f:
                files = {'file': (f"proposal_{os.path.basename(test_file)}", f, 'application/pdf' if test_file.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                response = requests.post(
                    f"{self.base_url}/api/upload?document_type=proposal",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                file_id = data.get('file_id')
                self.proposal_file_ids.append(file_id)
                
                # Verify response structure
                expected_fields = ['file_id', 'filename', 'document_type', 'is_active', 'upload_date']
                has_all_fields = all(field in data for field in expected_fields)
                correct_type = data.get('document_type') == 'proposal'
                is_active = data.get('is_active') == True
                
                passed = file_id and has_all_fields and correct_type and is_active
                return self.log_result(
                    "Proposal Upload",
                    passed,
                    f"File ID: {file_id}, Type: {data.get('document_type')}, Active: {data.get('is_active')}"
                )
            else:
                return self.log_result(
                    "Proposal Upload",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Proposal Upload", False, str(e))

    def test_list_documents_after_upload(self):
        """Test listing documents after uploads"""
        print("\n🔍 Testing List Documents (After Upload)...")
        try:
            response = requests.get(f"{self.base_url}/api/documents", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Should have at least 2 documents (1 contract, 1 proposal)
                has_documents = len(data) >= 2
                
                # Check document structure
                valid_structure = True
                for doc in data:
                    required_fields = ['file_id', 'filename', 'document_type', 'is_active', 'upload_date']
                    if not all(field in doc for field in required_fields):
                        valid_structure = False
                        break
                
                passed = has_documents and valid_structure
                return self.log_result(
                    "List Documents (After Upload)",
                    passed,
                    f"Retrieved {len(data)} documents with valid structure"
                )
            else:
                return self.log_result(
                    "List Documents (After Upload)",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("List Documents (After Upload)", False, str(e))

    def test_get_active_documents(self):
        """Test getting active documents"""
        print("\n🔍 Testing Get Active Documents...")
        try:
            response = requests.get(f"{self.base_url}/api/documents/active", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Should have contract and proposal keys
                has_structure = 'contract' in data and 'proposal' in data
                
                # Should have active contract and proposal
                has_active_contract = data.get('contract') is not None
                has_active_proposal = data.get('proposal') is not None
                
                passed = has_structure and has_active_contract and has_active_proposal
                return self.log_result(
                    "Get Active Documents",
                    passed,
                    f"Active contract: {bool(data.get('contract'))}, Active proposal: {bool(data.get('proposal'))}"
                )
            else:
                return self.log_result(
                    "Get Active Documents",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Get Active Documents", False, str(e))

    def test_set_active_document(self):
        """Test setting a document as active"""
        print("\n🔍 Testing Set Active Document...")
        if not self.contract_file_ids:
            return self.log_result("Set Active Document", False, "No contract file_id available")
        
        try:
            payload = {
                "file_id": self.contract_file_ids[0],
                "document_type": "contract"
            }
            response = requests.post(
                f"{self.base_url}/api/documents/set-active",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ['status', 'file_id', 'document_type', 'is_active']
                has_all_fields = all(field in data for field in expected_fields)
                correct_status = data.get('status') == 'success'
                is_active = data.get('is_active') == True
                
                passed = has_all_fields and correct_status and is_active
                return self.log_result(
                    "Set Active Document",
                    passed,
                    f"Status: {data.get('status')}, Active: {data.get('is_active')}"
                )
            else:
                return self.log_result(
                    "Set Active Document",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Set Active Document", False, str(e))

    def test_additive_uploads(self):
        """Test additive upload behavior - upload second contract"""
        print("\n🔍 Testing Additive Uploads (Second Contract)...")
        try:
            test_file = '/app/test_contract.pdf'
            if not os.path.exists(test_file):
                test_file = '/app/test_contract.docx'
            
            if not os.path.exists(test_file):
                return self.log_result("Additive Uploads", False, "No test file found")
            
            with open(test_file, 'rb') as f:
                files = {'file': (f"contract_b_{os.path.basename(test_file)}", f, 'application/pdf' if test_file.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                response = requests.post(
                    f"{self.base_url}/api/upload?document_type=contract",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
                new_file_id = data.get('file_id')
                self.contract_file_ids.append(new_file_id)
                
                # New contract should be active
                is_new_active = data.get('is_active') == True
                
                # Check that both contracts exist in list
                list_response = requests.get(f"{self.base_url}/api/documents", timeout=10)
                if list_response.status_code == 200:
                    docs = list_response.json()
                    contract_docs = [doc for doc in docs if doc.get('document_type') == 'contract']
                    
                    # Should have at least 2 contracts
                    has_multiple_contracts = len(contract_docs) >= 2
                    
                    # Only one should be active
                    active_contracts = [doc for doc in contract_docs if doc.get('is_active')]
                    only_one_active = len(active_contracts) == 1
                    
                    # The new one should be the active one
                    new_is_active = active_contracts[0].get('file_id') == new_file_id if active_contracts else False
                    
                    passed = is_new_active and has_multiple_contracts and only_one_active and new_is_active
                    return self.log_result(
                        "Additive Uploads",
                        passed,
                        f"Contracts: {len(contract_docs)}, Active: {len(active_contracts)}, New is active: {new_is_active}"
                    )
                else:
                    return self.log_result("Additive Uploads", False, "Failed to list documents")
            else:
                return self.log_result(
                    "Additive Uploads",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Additive Uploads", False, str(e))

    def test_proposal_independence(self):
        """Test that proposal uploads don't affect contract active status"""
        print("\n🔍 Testing Proposal Independence...")
        try:
            # Get current active contract
            active_response = requests.get(f"{self.base_url}/api/documents/active", timeout=10)
            if active_response.status_code != 200:
                return self.log_result("Proposal Independence", False, "Failed to get active documents")
            
            active_before = active_response.json()
            contract_before = active_before.get('contract')
            
            if not contract_before:
                return self.log_result("Proposal Independence", False, "No active contract found")
            
            # Upload another proposal
            test_file = '/app/test_contract.pdf'
            if not os.path.exists(test_file):
                test_file = '/app/test_contract.docx'
            
            with open(test_file, 'rb') as f:
                files = {'file': (f"proposal_b_{os.path.basename(test_file)}", f, 'application/pdf' if test_file.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                response = requests.post(
                    f"{self.base_url}/api/upload?document_type=proposal",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                # Check active documents again
                active_after_response = requests.get(f"{self.base_url}/api/documents/active", timeout=10)
                if active_after_response.status_code == 200:
                    active_after = active_after_response.json()
                    contract_after = active_after.get('contract')
                    
                    # Contract should remain the same
                    contract_unchanged = (contract_before.get('file_id') == contract_after.get('file_id') if contract_after else False)
                    
                    passed = contract_unchanged
                    return self.log_result(
                        "Proposal Independence",
                        passed,
                        f"Contract unchanged: {contract_unchanged}"
                    )
                else:
                    return self.log_result("Proposal Independence", False, "Failed to get active documents after proposal upload")
            else:
                return self.log_result(
                    "Proposal Independence",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Proposal Independence", False, str(e))

    def test_delete_document(self):
        """Test deleting a document"""
        print("\n🔍 Testing Delete Document...")
        if not self.contract_file_ids:
            return self.log_result("Delete Document", False, "No contract file_id available")
        
        try:
            # Use the first contract for deletion
            file_id_to_delete = self.contract_file_ids[0]
            
            response = requests.delete(
                f"{self.base_url}/api/documents/{file_id_to_delete}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                correct_status = data.get('status') == 'deleted'
                correct_file_id = data.get('file_id') == file_id_to_delete
                
                # Verify document is removed from list
                list_response = requests.get(f"{self.base_url}/api/documents", timeout=10)
                if list_response.status_code == 200:
                    docs = list_response.json()
                    file_ids = [doc.get('file_id') for doc in docs]
                    not_in_list = file_id_to_delete not in file_ids
                    
                    passed = correct_status and correct_file_id and not_in_list
                    return self.log_result(
                        "Delete Document",
                        passed,
                        f"Status: {data.get('status')}, Removed from list: {not_in_list}"
                    )
                else:
                    return self.log_result("Delete Document", False, "Failed to verify deletion in document list")
            else:
                return self.log_result(
                    "Delete Document",
                    False,
                    f"Status: {response.status_code}, Response: {response.text}"
                )
        except Exception as e:
            return self.log_result("Delete Document", False, str(e))

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*60)
        
        if self.tests_passed < self.tests_run:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")
        
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    print("="*60)
    print("🚀 Document Ingestion & Persistent Memory Testing")
    print("="*60)
    
    tester = DocumentIngestionTester()
    
    # Run document ingestion tests in sequence
    tester.test_health_check()
    tester.test_list_documents_empty()
    tester.test_upload_contract()
    tester.test_upload_proposal()
    tester.test_list_documents_after_upload()
    tester.test_get_active_documents()
    tester.test_set_active_document()
    tester.test_additive_uploads()
    tester.test_proposal_independence()
    tester.test_delete_document()
    
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
