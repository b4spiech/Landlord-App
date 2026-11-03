import { useRef, useState } from 'react';
import { getErrorMessage, propertyPhotoAPI } from '../services/api';
import { Card } from './ui';
import { useToast } from './Toast';

export const PropertyPhotoCard: React.FC<{ propertyId: string }> = ({ propertyId }) => {
  const toast = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  // null = unknown (still trying to load), true/false once the <img> resolves.
  const [hasPhoto, setHasPhoto] = useState<boolean | null>(null);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);

  const src = `${propertyPhotoAPI.photoUrl(propertyId)}?v=${version}`;

  const pickFile = () => fileInput.current?.click();

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await propertyPhotoAPI.upload(propertyId, form);
      toast.success('Photo updated');
      setHasPhoto(true);
      setVersion((v) => v + 1);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  };

  const remove = async () => {
    if (!confirm('Remove this photo?')) return;
    setBusy(true);
    try {
      await propertyPhotoAPI.remove(propertyId);
      setHasPhoto(false);
      setVersion((v) => v + 1);
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="font-semibold text-gray-900">Photo</h2>
        <div className="flex gap-3 text-sm">
          <button onClick={pickFile} disabled={busy} className="text-blue-600 font-medium hover:underline disabled:opacity-50">
            {hasPhoto ? 'Replace' : 'Add photo'}
          </button>
          {hasPhoto && (
            <button onClick={remove} disabled={busy} className="text-red-600 font-medium hover:underline disabled:opacity-50">
              Remove
            </button>
          )}
        </div>
      </div>

      {/* The image is always mounted so onLoad/onError can drive hasPhoto. */}
      <img
        src={src}
        alt="Property"
        onLoad={() => setHasPhoto(true)}
        onError={() => setHasPhoto(false)}
        className={`w-full object-cover max-h-[28rem] ${hasPhoto ? 'block' : 'hidden'}`}
      />

      {hasPhoto === false && (
        <button
          onClick={pickFile}
          disabled={busy}
          className="w-full flex flex-col items-center justify-center gap-2 py-16 text-gray-400 hover:text-gray-600 hover:bg-gray-50"
        >
          <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <path d="M21 15l-5-5L5 21" />
          </svg>
          <span className="text-sm font-medium">{busy ? 'Uploading…' : 'Add a property photo'}</span>
          <span className="text-xs">JPG, PNG, WEBP, or GIF · up to 10 MB</span>
        </button>
      )}

      {busy && hasPhoto && <div className="px-5 py-2 text-xs text-gray-500">Working…</div>}

      <input
        ref={fileInput}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0])}
      />
    </Card>
  );
};
