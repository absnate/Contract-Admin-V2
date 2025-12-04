import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const NewJob = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    manufacturer_name: '',
    domain: '',
    product_lines: [],
    sharepoint_folder: '',
    weekly_recrawl: false,
  });
  const [productLineInput, setProductLineInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAddProductLine = () => {
    if (productLineInput.trim()) {
      setFormData({
        ...formData,
        product_lines: [...formData.product_lines, productLineInput.trim()],
      });
      setProductLineInput('');
    }
  };

  const handleRemoveProductLine = (index) => {
    setFormData({
      ...formData,
      product_lines: formData.product_lines.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/crawl-jobs`, formData);
      toast.success('Crawl job created successfully!');
      navigate(`/job/${response.data.id}`);
    } catch (error) {
      toast.error('Failed to create crawl job: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
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
              <h1 className="text-2xl font-semibold tracking-tight font-sans">New Crawl Job</h1>
              <p className="text-sm text-muted-foreground font-body">Configure a new manufacturer documentation crawl</p>
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
                  <Label htmlFor="domain" className="text-xs uppercase tracking-widest font-medium">
                    Website Domain *
                  </Label>
                  <Input
                    id="domain"
                    data-testid="domain-input"
                    placeholder="e.g., https://www.example.com"
                    value={formData.domain}
                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">Full URL including https://</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="productLines" className="text-xs uppercase tracking-widest font-medium">
                    Product Lines (Optional)
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      id="productLines"
                      data-testid="product-line-input"
                      placeholder="e.g., XTR Series Actuators"
                      value={productLineInput}
                      onChange={(e) => setProductLineInput(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddProductLine())}
                    />
                    <Button type="button" onClick={handleAddProductLine} data-testid="add-product-line">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                  {formData.product_lines.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {formData.product_lines.map((line, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center gap-1 px-3 py-1 bg-secondary text-secondary-foreground rounded-md text-sm"
                          data-testid={`product-line-${index}`}
                        >
                          {line}
                          <button
                            type="button"
                            onClick={() => handleRemoveProductLine(index)}
                            className="hover:text-destructive"
                            data-testid={`remove-product-line-${index}`}
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">Restrict crawl to specific product lines or series</p>
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

                <div className="flex items-center space-x-2">
                  <Switch
                    id="recrawl"
                    data-testid="recrawl-switch"
                    checked={formData.weekly_recrawl}
                    onCheckedChange={(checked) => setFormData({ ...formData, weekly_recrawl: checked })}
                  />
                  <Label htmlFor="recrawl" className="text-sm font-normal cursor-pointer">
                    Enable weekly recrawl (every Sunday at midnight)
                  </Label>
                </div>

                <div className="flex gap-3 pt-4 border-t border-border">
                  <Button type="submit" disabled={loading} data-testid="submit-job">
                    {loading ? 'Creating...' : 'Start Crawl Job'}
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
              <h3 className="font-semibold text-sm mb-4 tracking-tight">How It Works</h3>
              <ol className="space-y-3 text-sm text-muted-foreground">
                <li className="flex gap-3">
                  <span className="font-mono text-primary font-medium">1.</span>
                  <span>Agent crawls the manufacturer's website looking for PDF links</span>
                </li>
                <li className="flex gap-3">
                  <span className="font-mono text-primary font-medium">2.</span>
                  <span>Gemini AI classifies each PDF as technical or marketing</span>
                </li>
                <li className="flex gap-3">
                  <span className="font-mono text-primary font-medium">3.</span>
                  <span>Technical PDFs are uploaded to your SharePoint folder</span>
                </li>
                <li className="flex gap-3">
                  <span className="font-mono text-primary font-medium">4.</span>
                  <span>Weekly recrawl detects and uploads new documents</span>
                </li>
              </ol>
            </Card>

            <Card className="border border-border bg-card shadow-none rounded-md p-6">
              <h3 className="font-semibold text-sm mb-4 tracking-tight">Technical Documents</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Technical Data Sheets (TDS)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Product Data Sheets (PDS)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Specification & Cut Sheets</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Installation Manuals</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Operation & Maintenance</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span>Engineering Diagrams</span>
                </li>
              </ul>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default NewJob;