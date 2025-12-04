import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ArrowLeft, Trash2, Calendar, Clock, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Schedules = () => {
  const queryClient = useQueryClient();

  const { data: schedules, isLoading } = useQuery({
    queryKey: ['schedules'],
    queryFn: async () => {
      const res = await axios.get(`${API_URL}/api/schedules`);
      return res.data;
    },
  });

  const deleteScheduleMutation = useMutation({
    mutationFn: async (scheduleId) => {
      await axios.delete(`${API_URL}/api/schedules/${scheduleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['schedules']);
      toast.success('Schedule deleted successfully');
    },
    onError: (error) => {
      toast.error('Failed to delete schedule: ' + (error.response?.data?.detail || error.message));
    },
  });

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
              <h1 className="text-2xl font-semibold tracking-tight font-sans">Scheduled Recrawls</h1>
              <p className="text-sm text-muted-foreground font-body">Manage weekly recrawl schedules</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto p-6">
        <Card className="border border-border bg-card shadow-none rounded-md">
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-tight">Active Schedules</h2>
              <Badge variant="secondary" className="font-mono">
                {schedules?.length || 0} schedules
              </Badge>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border bg-muted/30">
                <tr>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Manufacturer</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Domain</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Schedule</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">Last Run</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground font-mono">Next Run</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Status</th>
                  <th className="text-left p-4 text-xs uppercase tracking-widest font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan="7" className="p-8 text-center text-muted-foreground">
                      <Clock className="w-12 h-12 animate-spin mx-auto mb-4 text-muted-foreground/50" />
                      <p>Loading schedules...</p>
                    </td>
                  </tr>
                ) : schedules && schedules.length > 0 ? (
                  schedules.map((schedule) => (
                    <tr key={schedule.id} className="border-b border-border data-row transition-colors" data-testid={`schedule-row-${schedule.id}`}>
                      <td className="p-4 font-medium">{schedule.manufacturer_name}</td>
                      <td className="p-4 font-mono text-sm text-muted-foreground">{schedule.domain}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-primary" />
                          <span className="text-sm">Weekly (Sunday 00:00)</span>
                        </div>
                      </td>
                      <td className="p-4 font-mono text-sm text-muted-foreground">
                        {schedule.last_run ? new Date(schedule.last_run).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="p-4 font-mono text-sm text-muted-foreground">
                        {schedule.next_run ? new Date(schedule.next_run).toLocaleDateString() : 'Pending'}
                      </td>
                      <td className="p-4">
                        {schedule.enabled ? (
                          <Badge variant="default" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary">Disabled</Badge>
                        )}
                      </td>
                      <td className="p-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteScheduleMutation.mutate(schedule.id)}
                          disabled={deleteScheduleMutation.isLoading}
                          data-testid={`delete-schedule-${schedule.id}`}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7" className="p-8 text-center text-muted-foreground">
                      <AlertCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
                      <p>No schedules configured yet.</p>
                      <p className="text-sm mt-2">Create a crawl job with "Enable weekly recrawl" to add schedules.</p>
                      <Link to="/new-job">
                        <Button className="mt-4" data-testid="create-job-with-schedule">
                          Create Crawl Job
                        </Button>
                      </Link>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Info Card */}
        <Card className="border border-border bg-card shadow-none rounded-md p-6 mt-6">
          <h3 className="font-semibold text-sm mb-4 tracking-tight">About Weekly Recrawls</h3>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li className="flex gap-3">
              <span className="text-primary">•</span>
              <span>Schedules run every Sunday at midnight (00:00 UTC)</span>
            </li>
            <li className="flex gap-3">
              <span className="text-primary">•</span>
              <span>New and updated PDFs are automatically detected and uploaded</span>
            </li>
            <li className="flex gap-3">
              <span className="text-primary">•</span>
              <span>Each recrawl creates a new job instance for tracking</span>
            </li>
            <li className="flex gap-3">
              <span className="text-primary">•</span>
              <span>Duplicate PDFs are automatically skipped based on filename and size</span>
            </li>
          </ul>
        </Card>
      </main>
    </div>
  );
};

export default Schedules;