import { useEffect, useRef, useState } from 'react';
import { getErrorMessage, hoaDocumentAPI } from '../services/api';
import type { HOADocument } from '../types';
import { Button, Card, Spinner } from './ui';
import { Field, Select, TextInput } from './FormFields';
import { useToast } from './Toast';
import { formatDate, titleCase } from '../lib/format';

const DOC_TYPES = [
  { value: 'ccr', label: 'CC&Rs' },
  { value: 'bylaws', label: 'Bylaws' },
  { value: 'rules', label: 'Rules & Regulations' },
  { value: 'budget', label: 'Budget' },
  { value: 'meeting_minutes', label: 'Meeting Minutes' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'other', label: 'Other' },
];

function humanSize(bytes?: number | null): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const HOADocuments: React.FC<{ hoaId: string }> = ({ hoaId }) => {
  const toast = useToast();
  const [docs, setDocs] = useState<HOADocument[] | null>(null);
  const [name, setName] = useState('');
  const [docType, setDocType] = useState('ccr');
  const [externalUrl, setExternalUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = () => {
    hoaDocumentAPI
      .list(hoaId)
      .then(setDocs)
      .catch((err) => toast.error(getErrorMessage(err)));
  };

  useEffect(load, [hoaId]); // eslint-disable-line react-hooks/exhaustive-deps

  const reset = () => {
    setName('');
    setDocType('ccr');
    setExternalUrl('');
    setFile(null);
    if (fileInput.current) fileInput.current.value = '';
  };

  const handleUpload = async () => {
    if (!name.trim()) return toast.error('Give the document a name');
    if (!file && !externalUrl.trim()) return toast.error('Choose a file or enter a link');
    setUploading(true);
    try {
      const form = new FormData();
      form.append('name', name.trim());
      form.append('doc_type', docType);
      if (file) form.append('file', file);
      if (externalUrl.trim()) form.append('external_url', externalUrl.trim());
      await hoaDocumentAPI.upload(hoaId, form);
      toast.success('Document added');
      reset();
      load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (doc: HOADocument) => {
    if (!confirm(`Delete “${doc.name}”?`)) return;
    try {
      await hoaDocumentAPI.remove(hoaId, doc.id);
      toast.success('Document deleted');
      load();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <Card>
      <div className="px-5 py-4 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">Documents</h2>
      </div>

      {docs === null ? (
        <Spinner />
      ) : docs.length === 0 ? (
        <p className="px-5 py-6 text-sm text-gray-500">No documents yet.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {docs.map((d) => (
            <li key={d.id} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="font-medium text-gray-900">{d.name}</p>
                <p className="text-xs text-gray-500">
                  {titleCase(d.doc_type)}
                  {d.has_file
                    ? ` · ${d.filename ?? 'file'} · ${humanSize(d.file_size)}`
                    : ' · external link'}{' '}
                  · {formatDate(d.uploaded_at)}
                </p>
              </div>
              <div className="flex items-center gap-3 text-sm">
                {d.has_file ? (
                  <a
                    href={hoaDocumentAPI.downloadUrl(hoaId, d.id)}
                    className="text-blue-600 font-medium hover:underline"
                  >
                    Download
                  </a>
                ) : (
                  <a
                    href={d.external_url ?? '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 font-medium hover:underline"
                  >
                    Open
                  </a>
                )}
                <button
                  onClick={() => handleDelete(d)}
                  className="text-red-600 font-medium hover:underline"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Upload form */}
      <div className="px-5 py-4 border-t border-gray-200 bg-gray-50 space-y-3">
        <p className="text-sm font-medium text-gray-700">Add a document</p>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Name">
            <TextInput value={name} onChange={setName} placeholder="CC&Rs (2024)" />
          </Field>
          <Field label="Type">
            <Select value={docType} onChange={setDocType} options={DOC_TYPES} />
          </Field>
        </div>
        <Field label="File">
          <input
            ref={fileInput}
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700"
          />
        </Field>
        <Field label="…or external link">
          <TextInput value={externalUrl} onChange={setExternalUrl} placeholder="https://drive.google.com/…" />
        </Field>
        <div className="flex justify-end">
          <Button onClick={handleUpload} disabled={uploading}>
            {uploading ? 'Uploading…' : 'Add document'}
          </Button>
        </div>
      </div>
    </Card>
  );
};
