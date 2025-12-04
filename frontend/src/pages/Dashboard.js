import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { FileText, Clock, CheckCircle2, AlertCircle, Plus, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Dashboard = () => {
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/api/stats`);
      return res.data;
    },
    refetchInterval: 5000,
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/api/crawl-jobs`);
      return res.data;
    },
    refetchInterval: 5000,
  });

  const getStatusColor = (status) => {
    const colors = {
      pending: 'text-blue-500',
      crawling: 'text-amber-500',
      classifying: 'text-purple-500',
      uploading: 'text-cyan-500',
      completed: 'text-emerald-500',
      failed: 'text-red-500',
    };
    return colors[status] || 'text-muted-foreground';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight font-sans">PDF DocSync Agent</h1>
            <p className="text-sm text-muted-foreground font-body">Automated technical documentation crawler</p>
          </div>
          <div className="flex gap-3">
            <Link to="/schedules">
              <Button variant="outline" data-testid="schedules-button">
                <Calendar className="w-4 h-4 mr-2" />
                Schedules
              </Button>
            </Link>
            <Link to="/new-job">
              <Button data-testid="new-job-button">
                <Plus className="w-4 h-4 mr-2" />
                New Crawl Job
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="stat-card" data-testid="stat-total-jobs">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Total Jobs</p>
                <p className="text-3xl font-semibold mt-2">{stats?.total_jobs || 0}</p>
              </div>
              <FileText className="w-8 h-8 text-primary" strokeWidth={1.5} />
            </div>
          </Card>

          <Card className="stat-card" data-testid="stat-active-jobs">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Active Jobs</p>
                <p className="text-3xl font-semibold mt-2">{stats?.active_jobs || 0}</p>
              </div>
              <Clock className="w-8 h-8 text-amber-500" strokeWidth={1.5} />
            </div>
          </Card>

          <Card className="stat-card" data-testid="stat-technical-pdfs">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Technical PDFs</p>
                <p className="text-3xl font-semibold mt-2">{stats?.technical_pdfs || 0}</p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-emerald-500" strokeWidth={1.5} />
            </div>
          </Card>

          <Card className="stat-card" data-testid="stat-uploaded">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Uploaded</p>
                <p className="text-3xl font-semibold mt-2">{stats?.uploaded_pdfs || 0}</p>
              </div>
              <FileText className="w-8 h-8 text-cyan-500" strokeWidth={1.5} />
            </div>
          </Card>
        </div>

        {/* Recent Jobs */}
        <Card className="border border-border bg-card shadow-none rounded-md">
          <div className="p-6 border-b border-border">
            <h2 className="text-lg font-semibold tracking-tight">Recent Crawl Jobs</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border bg-muted/30">
                <tr>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Manufacturer</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Domain</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Status</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">PDFs Found</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">Technical</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">Uploaded</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">Created</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Action</th>
                </tr>
              </thead>
              <tbody>
                {jobs && jobs.length > 0 ? (
                  jobs.slice(0, 10).map((job) => (
                    <tr key={job.id} className="border-b border-border data-row transition-colors" data-testid={`job-row-${job.id}`}>
                      <td className="p-4 font-medium">{job.manufacturer_name}</td>
                      <td className="p-4 font-mono text-sm text-muted-foreground">{job.domain}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border status-${job.status}`} data-testid={`job-status-${job.id}`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="p-4 font-mono text-sm">{job.total_pdfs_found}</td>
                      <td className="p-4 font-mono text-sm">{job.total_pdfs_classified}</td>
                      <td className="p-4 font-mono text-sm">{job.total_pdfs_uploaded}</td>
                      <td className="p-4 font-mono text-sm text-muted-foreground">
                        {new Date(job.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <Link to={`/job/${job.id}`}>
                          <Button variant="ghost" size="sm" data-testid={`view-job-${job.id}`}>
                            View
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="8" className="p-8 text-center text-muted-foreground">
                      <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
                      <p>No crawl jobs yet. Create your first job to get started.</p>
                      <Link to="/new-job">
                        <Button className="mt-4" data-testid="create-first-job">
                          Create First Job
                        </Button>
                      </Link>
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

export default Dashboard;