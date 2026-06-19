import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getErrorMessage, leaseImportAPI } from '../services/api';
import type { CreateLeaseResult, ParsedLeaseData } from '../types';
import { Button, Card, PageHeader, Spinner } from '../components/ui';
import { LeaseReviewEditor } from '../components/LeaseReviewEditor';
import { useToast } from '../components/Toast';

const EMPTY_PARSED: ParsedLeaseData = { tenants: [{}], lease: {}, confidence: 'low', notes: null };

export const LeaseImportPage = () => {
  const toast = useToast();
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [parsing, setParsing] = useState(false);

  const [parsed, setParsed] = useState<ParsedLeaseData | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [mode, setMode] = useState<'upload' | 'review'>('upload');

  const handleParse = async () => {
    if (!file) return toast.error('Choose a PDF or image first');
    setParsing(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await leaseImportAPI.parseDocument(form);
      setParsed(res.parsed);
      setDocumentId(res.document_id);
      setMode('review');
      toast.success('Document parsed — review the details below');
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setParsing(false);
    }
  };

  const handleManual = () => {
    setParsed(EMPTY_PARSED);
    setDocumentId(null);
    setMode('review');
  };

  const handleCreated = (r: CreateLeaseResult) => {
    toast.success(`Lease created with ${r.tenants_created} tenant(s)`);
    navigate('/leases');
  };

  if (mode === 'review' && parsed) {
    return (
      <div>
        <PageHeader
          title={documentId ? 'Review Extracted Lease' : 'Enter Lease Manually'}
          subtitle={documentId ? 'Check the AI-extracted data, edit as needed, then create the lease.' : undefined}
        />
        <LeaseReviewEditor
          initial={parsed}
          documentId={documentId}
          onCreated={handleCreated}
          onCancel={() => setMode('upload')}
        />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <PageHeader title="Import Lease" subtitle="Upload a lease document and let AI extract the details" />
      <Card className="p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Lease document (PDF, JPG, or PNG — up to 10 pages)
          </label>
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700"
          />
          {file && <p className="text-xs text-gray-500 mt-2">{file.name} ({Math.round(file.size / 1024)} KB)</p>}
        </div>

        {parsing ? (
          <Spinner label="Parsing document with AI… this can take up to a minute." />
        ) : (
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleParse} disabled={!file}>
              Parse Lease Document
            </Button>
            <Button variant="secondary" onClick={handleManual}>
              Enter Data Manually
            </Button>
          </div>
        )}

        <p className="text-xs text-gray-500">
          AI extraction requires the server to be configured with an Anthropic API key. If parsing
          isn't available, use “Enter Data Manually”.
        </p>
      </Card>
    </div>
  );
};
