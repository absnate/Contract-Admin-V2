import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileText, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BulkUploadDetails = () => {
  const { jobId } = useParams();

  const { data: job, isLoading } = useQuery({
    queryKey: ['bulk-upload-job', jobId],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/api/bulk-upload-jobs/${jobId}`);
      return res.data;
    },
    refetchInterval: 5000,
  });

  const { data: pdfs } = useQuery({
    queryKey: ['bulk-upload-pdfs', jobId],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/api/bulk-upload-jobs/${jobId}/pdfs`);
      return res.data;
    },
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Clock className="w-12 h-12 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-muted-foreground">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-12 h-12 mx-auto mb-4 text-destructive" />
          <p className="text-muted-foreground">Job not found</p>
          <Link to="/">
            <Button className="mt-4">Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  const calculateProgress = () => {
    if (job.status === 'completed') return 100;
    if (job.status === 'uploading') return 80;
    if (job.status === 'downloading') return 60;
    if (job.status === 'processing') return 40;
    if (job.status === 'pending') return 20;
    return 0;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm" data-testid="back-to-dashboard">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight font-sans">{job.manufacturer_name}</h1>
              <p className="text-sm text-muted-foreground font-body">Bulk Upload Job</p>
            </div>
          </div>
          <span className={`inline-flex items-center px-3 py-1.5 rounded text-sm font-medium border status-${job.status}`} data-testid="job-status">
            {job.status}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto p-6 space-y-6">
        {/* Progress */}
        {job.status !== 'completed' && job.status !== 'failed' && (
          <Card className="border border-border bg-card shadow-none rounded-md p-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Upload Progress</p>
                <p className="text-sm text-muted-foreground">{calculateProgress()}%</p>
              </div>
              <Progress value={calculateProgress()} className="h-2" data-testid="progress-bar" />
              <p className="text-xs text-muted-foreground capitalize">Status: {job.status}</p>
            </div>
          </Card>
        )}

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="stat-card" data-testid="stat-items">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Total Items</p>
                <p className="text-3xl font-semibold mt-2">{job.total_items}</p>
              </div>
              <FileText className="w-8 h-8 text-blue-500" strokeWidth={1.5} />
            </div>
          </Card>

          <Card className="stat-card" data-testid="stat-classified">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Classified</p>
                <p className="text-3xl font-semibold mt-2">{job.total_classified}</p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-purple-500" strokeWidth={1.5} />
            </div>
          </Card>

          <Card className="stat-card" data-testid="stat-technical">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Technical</p>
                <p className="text-3xl font-semibold mt-2">
                  {pdfs?.filter((p) => p.is_technical).length || 0}
                </p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-emerald-500" strokeWidth={1.5} />
            </div>
          </Card>

          <Card className="stat-card" data-testid="stat-uploaded">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Uploaded</p>
                <p className="text-3xl font-semibold mt-2">{job.total_uploaded}</p>
              </div>
              <FileText className="w-8 h-8 text-cyan-500" strokeWidth={1.5} />
            </div>
          </Card>
        </div>

        {/* PDF List */}
        <Card className="border border-border bg-card shadow-none rounded-md">
          <div className="p-6 border-b border-border">
            <h2 className="text-lg font-semibold tracking-tight">Processed PDFs</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border bg-muted/30">
                <tr>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Part Number</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Filename</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Document Type</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Classification</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Status</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">Size</th>
                </tr>
              </thead>
              <tbody>
                {pdfs && pdfs.length > 0 ? (
                  pdfs.map((pdf) => (
                    <tr key={pdf.id} className="border-b border-border data-row transition-colors" data-testid={`pdf-row-${pdf.id}`}>
                      <td className="p-4 font-mono text-sm font-medium">{pdf.part_number}</td>
                      <td className="p-4">
                        <a
                          href={pdf.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline font-medium"
                          data-testid={`pdf-link-${pdf.id}`}
                        >
                          {pdf.filename}
                        </a>
                      </td>
                      <td className="p-4 text-sm text-muted-foreground">{pdf.document_type || 'N/A'}</td>
                      <td className="p-4">
                        {pdf.is_technical ? (
                          <Badge variant="default" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                            Technical
                          </Badge>
                        ) : (
                          <Badge variant="secondary">Marketing</Badge>
                        )}
                      </td>
                      <td className="p-4">
                        {pdf.sharepoint_uploaded ? (
                          <Badge variant="default" className="bg-cyan-500/10 text-cyan-500 border-cyan-500/20">
                            Uploaded
                          </Badge>
                        ) : (
                          <Badge variant="outline">Pending</Badge>
                        )}
                      </td>
                      <td className="p-4 font-mono text-sm text-muted-foreground">
                        {(pdf.file_size / 1024).toFixed(1)} KB
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="p-8 text-center text-muted-foreground">
                      <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
                      <p>No PDFs processed yet. Upload is in progress...</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </main>
    </div>
  );
};

export default BulkUploadDetails;
