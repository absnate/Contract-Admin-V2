import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/sonner';
import Dashboard from './pages/Dashboard';
import NewJob from './pages/NewJob';
import JobDetails from './pages/JobDetails';
import Schedules from './pages/Schedules';
import BulkUpload from './pages/BulkUpload';
import BulkUploadDetails from './pages/BulkUploadDetails';
import ActiveJobs from './pages/ActiveJobs';
import '@/App.css';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-job" element={<NewJob />} />
            <Route path="/job/:jobId" element={<JobDetails />} />
            <Route path="/schedules" element={<Schedules />} />
            <Route path="/bulk-upload" element={<BulkUpload />} />
            <Route path="/bulk-upload/:jobId" element={<BulkUploadDetails />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </QueryClientProvider>
  );
}

export default App;