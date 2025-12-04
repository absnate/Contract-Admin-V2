import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Upload, FileSpreadsheet, Download, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BulkUpload = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    manufacturer_name: '',
    sharepoint_folder: '',
  });
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls')) {
        toast.error('Please select an Excel file (.xlsx or .xls)');
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      toast.error('Please select an Excel file');
      return;
    }

    setLoading(true);

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('file', file);

      const response = await axios.post(
        `${API_URL}/api/bulk-upload?manufacturer_name=${encodeURIComponent(formData.manufacturer_name)}&sharepoint_folder=${encodeURIComponent(formData.sharepoint_folder)}`,
        formDataToSend,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      toast.success('Bulk upload job created successfully!');
      navigate(`/bulk-upload/${response.data.id}`);
    } catch (error) {
      toast.error('Failed to create bulk upload job: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = () => {
    // Create a sample CSV content matching the user's format
    const csvContent = 'Part Number,Technical Product Data\n8570-001420,https://www.example.com/datasheet1.pdf\n926-120000,https://www.example.com/datasheet2.pdf\n356-000000,https://www.example.com/manual.pdf';
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'bulk_upload_template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm" data-testid="back-button">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight font-sans">Bulk Upload from Excel</h1>
              <p className="text-sm text-muted-foreground font-body">Upload Excel file with part numbers and PDF URLs</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Form */}
          <div className="lg:col-span-2">
            <Card className="border border-border bg-card shadow-none rounded-md p-6">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="manufacturer" className="text-xs uppercase tracking-widest font-medium">
                    Manufacturer Name *
                  </Label>
                  <Input
                    id="manufacturer"
                    data-testid="manufacturer-input"
                    placeholder="e.g., Acme Controls"
                    value={formData.manufacturer_name}
                    onChange={(e) => setFormData({ ...formData, manufacturer_name: e.target.value })}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="sharepoint" className="text-xs uppercase tracking-widest font-medium">
                    SharePoint Folder Path *
                  </Label>
                  <Input
                    id="sharepoint"
                    data-testid="sharepoint-input"
                    placeholder="e.g., /Product Data/HVAC/Manufacturer Name"
                    value={formData.sharepoint_folder}
                    onChange={(e) => setFormData({ ...formData, sharepoint_folder: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">Relative path from site root</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="file" className="text-xs uppercase tracking-widest font-medium">
                    Excel File *
                  </Label>
                  <div className="border-2 border-dashed border-border rounded-md p-6 text-center hover:border-primary/50 transition-colors">
                    <input
                      type="file"
                      id="file"
                      data-testid="file-input"
                      accept=".xlsx,.xls"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    <label htmlFor="file" className="cursor-pointer">
                      {file ? (
                        <div className="flex items-center justify-center gap-3">
                          <FileSpreadsheet className="w-8 h-8 text-primary" />
                          <div className="text-left">
                            <p className="font-medium">{file.name}</p>
                            <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(2)} KB</p>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                          <p className="font-medium mb-2">Click to upload Excel file</p>
                          <p className="text-sm text-muted-foreground">Supports .xlsx and .xls files</p>
                        </div>
                      )}
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    File must have two columns: Part Number (Column A) and PDF URL (Column B)
                  </p>
                </div>

                <div className="flex gap-3 pt-4 border-t border-border">
                  <Button type="submit" disabled={loading || !file} data-testid="submit-bulk-upload">
                    {loading ? 'Processing...' : 'Start Bulk Upload'}
                  </Button>
                  <Link to="/">
                    <Button type="button" variant="outline" data-testid="cancel-button">
                      Cancel
                    </Button>
                  </Link>
                </div>
              </form>
            </Card>
          </div>

          {/* Instructions */}
          <div className="space-y-6">
            <Card className="border border-border bg-card shadow-none rounded-md p-6">
              <h3 className="font-semibold text-sm mb-4 tracking-tight">Excel File Format</h3>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="flex gap-3">
                  <span className="font-mono text-primary font-medium">1.</span>
                  <span>First row should be headers (will be skipped)</span>
                </div>
                <div className="flex gap-3">
                  <span className="font-mono text-primary font-medium">2.</span>
                  <span>Column A: Part Number (e.g., 8570-001420)</span>
                </div>
                <div className="flex gap-3">
                  <span className="font-mono text-primary font-medium">3.</span>
                  <span>Column B: Technical Product Data (Full URL to PDF)</span>
                </div>
                <div className="flex gap-3">
                  <span className="font-mono text-primary font-medium">4.</span>
                  <span>URLs must start with http:// or https://</span>
                </div>
              </div>
              <Button
                variant="outline"
                className="w-full mt-4"
                onClick={downloadTemplate}
                data-testid="download-template"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Sample Template
              </Button>
            </Card>

            <Card className="border border-border bg-card shadow-none rounded-md p-6">
              <h3 className="font-semibold text-sm mb-4 tracking-tight">Processing Steps</h3>
              <ol className="space-y-3 text-sm text-muted-foreground">
                <li className="flex gap-3">
                  <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span>Parse Excel file and validate URLs</span>
                </li>
                <li className="flex gap-3">
                  <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span>Download PDFs from provided URLs</span>
                </li>
                <li className="flex gap-3">
                  <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span>Gemini AI classifies each PDF</span>
                </li>
                <li className="flex gap-3">
                  <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                  <span>Technical PDFs uploaded to SharePoint</span>
                </li>
              </ol>
            </Card>

            <Card className="border border-primary/20 bg-primary/5 shadow-none rounded-md p-6">
              <h3 className="font-semibold text-sm mb-2 tracking-tight text-primary">Important Note</h3>
              <p className="text-sm text-muted-foreground">
                All PDF URLs must be publicly accessible. Password-protected or authentication-required URLs will fail to download.
              </p>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default BulkUpload;
