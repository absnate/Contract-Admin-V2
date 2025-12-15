import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ArrowLeft, StopCircle, Clock, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ActiveJobs = () => {
  const queryClient = useQueryClient();

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['active-jobs'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/api/active-jobs`);
      return res.data;
    },
    refetchInterval: 1000, // Refresh every 1 second (faster feedback on cancellation)
  });

  const cancelCrawlMutation = useMutation({
    mutationFn: async (jobId) => {
      await axios.post(`${API_URL}/api/crawl-jobs/${jobId}/cancel`);
    },
    onSuccess: (_data, jobId) => {
      // Optimistic UI: remove immediately, then refetch
      queryClient.setQueryData(['active-jobs'], (old) => (old ? old.filter((j) => j.id !== jobId) : old));
      queryClient.invalidateQueries(['active-jobs']);
      toast.success('Crawl job cancelled successfully');
    },
    onError: (error) => {
      toast.error('Failed to cancel job: ' + (error.response?.data?.detail || error.message));
    },
  });

  const cancelBulkMutation = useMutation({
    mutationFn: async (jobId) => {
      await axios.post(`${API_URL}/api/bulk-upload-jobs/${jobId}/cancel`);
    },
    onSuccess: (_data, jobId) => {
      queryClient.setQueryData(['active-jobs'], (old) => (old ? old.filter((j) => j.id !== jobId) : old));
      queryClient.invalidateQueries(['active-jobs']);
      toast.success('Bulk upload job cancelled successfully');
    },
    onError: (error) => {
      toast.error('Failed to cancel job: ' + (error.response?.data?.detail || error.message));
    },
  });

  const handleCancel = (job) => {
    // Avoid window.confirm (can be blocked by some browsers/iframes); cancel immediately and show feedback.
    if (job.job_type === 'crawl') {
      cancelCrawlMutation.mutate(job.id);
    } else {
      cancelBulkMutation.mutate(job.id);
    }
  };

  const getProgress = (job) => {
    if (job.job_type === 'crawl') {
      if (job.status === 'completed') return 100;
      if (job.status === 'uploading') return 80;
      if (job.status === 'classifying') return 60;
      if (job.status === 'crawling') return 40;
      return 20;
    } else {
      if (job.status === 'completed') return 100;
      if (job.status === 'uploading') return 70;
      if (job.status === 'downloading') return 40;
      if (job.status === 'processing') return 20;
      return 10;
    }
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
              <h1 className="text-2xl font-semibold tracking-tight font-sans">Active Jobs</h1>
              <p className="text-sm text-muted-foreground font-body">Monitor and manage running jobs</p>
            </div>
          </div>
          <Badge variant="secondary" className="font-mono">
            {jobs?.length || 0} active
          </Badge>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Clock className="w-12 h-12 animate-spin text-primary" />
          </div>
        ) : jobs && jobs.length > 0 ? (
          <div className="space-y-6">
            {jobs.map((job) => (
              <Card key={job.id} className="border border-border bg-card shadow-none rounded-md p-6" data-testid={`active-job-${job.id}`}>
                <div className="space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold">{job.manufacturer_name}</h3>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {job.job_type === 'crawl' ? 'Web Crawl' : 'Bulk Upload'}
                        </Badge>
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border status-${job.status}`}>
                          {job.status}
                        </span>
                      </div>
                      {job.job_type === 'crawl' ? (
                        <p className="text-sm text-muted-foreground font-mono">{job.domain}</p>
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          Processing {job.total_items} items from Excel
                        </p>
                      )}
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleCancel(job)}
                      disabled={cancelCrawlMutation.isLoading || cancelBulkMutation.isLoading}
                      data-testid={`cancel-job-${job.id}`}
                    >
                      <StopCircle className="w-4 h-4 mr-2" />
                      Stop Job
                    </Button>
                  </div>

                  {/* Progress */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-mono">{getProgress(job)}%</span>
                    </div>
                    <Progress value={getProgress(job)} className="h-2" />
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {job.job_type === 'crawl' ? (
                      <>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">PDFs Found</p>
                          <p className="text-2xl font-semibold font-mono">{job.total_pdfs_found}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Classified</p>
                          <p className="text-2xl font-semibold font-mono">{job.total_pdfs_classified}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Uploaded</p>
                          <p className="text-2xl font-semibold font-mono">{job.total_pdfs_uploaded}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Started</p>
                          <p className="text-sm font-mono text-muted-foreground">
                            {new Date(job.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Total Items</p>
                          <p className="text-2xl font-semibold font-mono">{job.total_items}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Processed</p>
                          <p className="text-2xl font-semibold font-mono">{job.total_classified}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Uploaded</p>
                          <p className="text-2xl font-semibold font-mono">{job.total_uploaded}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground uppercase tracking-widest">Started</p>
                          <p className="text-sm font-mono text-muted-foreground">
                            {new Date(job.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </>
                    )}
                  </div>

                  {/* View Details Link */}
                  <div className="pt-2 border-t border-border">
                    <Link
                      to={job.job_type === 'crawl' ? `/job/${job.id}` : `/bulk-upload/${job.id}`}
                      className="text-sm text-primary hover:underline"
                    >
                      View detailed results →
                    </Link>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="border border-border bg-card shadow-none rounded-md p-12">
            <div className="text-center">
              <AlertCircle className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
              <h3 className="text-lg font-semibold mb-2">No Active Jobs</h3>
              <p className="text-muted-foreground mb-6">
                All jobs are completed or no jobs have been started yet.
              </p>
              <div className="flex gap-3 justify-center">
                <Link to="/new-job">
                  <Button>Start Web Crawl</Button>
                </Link>
                <Link to="/bulk-upload">
                  <Button variant="outline">Start Bulk Upload</Button>
                </Link>
              </div>
            </div>
          </Card>
        )}
      </main>
    </div>
  );
};

export default ActiveJobs;
