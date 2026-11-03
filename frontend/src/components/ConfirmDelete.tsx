import { useState } from 'react';
import { deleteAPI, getErrorMessage, type DeletableKind } from '../services/api';
import { useAsync } from '../lib/useAsync';
import { Button } from './ui';
import { Modal } from './Modal';
import { useToast } from './Toast';

const LABELS: Record<DeletableKind, string> = {
  properties: 'property',
  hoas: 'HOA',
  owners: 'owner',
  'management-companies': 'management company',
  tenants: 'tenant',
  leases: 'lease',
};

const CONFIRM_WORD = 'DELETE';

/**
 * Delete button + warning dialog. The dialog asks the server what deleting
 * would do (what blocks it, what else is deleted or unlinked) and only enables
 * the red button after the user types DELETE.
 */
export const DeleteButton = ({
  kind,
  id,
  onDeleted,
  variant = 'button',
}: {
  kind: DeletableKind;
  id: string;
  onDeleted: () => void;
  variant?: 'button' | 'link';
}) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      {variant === 'button' ? (
        <Button
          variant="secondary"
          className="text-red-700 hover:bg-red-50"
          onClick={() => setOpen(true)}
        >
          Delete
        </Button>
      ) : (
        <button onClick={() => setOpen(true)} className="text-red-600 hover:underline">
          Delete
        </button>
      )}
      {open && (
        <ConfirmDeleteModal
          kind={kind}
          id={id}
          onClose={() => setOpen(false)}
          onDeleted={onDeleted}
        />
      )}
    </>
  );
};

const ConfirmDeleteModal = ({
  kind,
  id,
  onClose,
  onDeleted,
}: {
  kind: DeletableKind;
  id: string;
  onClose: () => void;
  onDeleted: () => void;
}) => {
  const toast = useToast();
  const label = LABELS[kind];
  const { data: plan, loading, error } = useAsync(() => deleteAPI.preview(kind, id), [kind, id]);
  const [typed, setTyped] = useState('');
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    setBusy(true);
    try {
      await deleteAPI.remove(kind, id);
      toast.success(`Deleted ${label} “${plan?.name}”`);
      onClose();
      onDeleted();
    } catch (err) {
      toast.error(getErrorMessage(err));
      setBusy(false);
    }
  };

  return (
    <Modal open title={`Delete ${label}?`} onClose={onClose}>
      {loading && <p className="text-sm text-gray-500">Checking what this would affect…</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}
      {plan && !plan.can_delete && (
        <div className="space-y-4">
          <p className="text-sm text-gray-800">
            <strong>{plan.name}</strong> can't be deleted yet because:
          </p>
          <ul className="list-disc pl-5 text-sm text-gray-800 space-y-1">
            {plan.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
          <div className="flex justify-end">
            <Button variant="secondary" onClick={onClose}>
              OK
            </Button>
          </div>
        </div>
      )}
      {plan && plan.can_delete && (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (typed === CONFIRM_WORD) confirm();
          }}
        >
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            <p>
              You're about to permanently delete the {label} <strong>{plan.name}</strong>. This
              can't be undone.
            </p>
            {plan.also_deletes.length > 0 && (
              <>
                <p className="mt-2 font-medium">This will also permanently delete:</p>
                <ul className="list-disc pl-5">
                  {plan.also_deletes.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </>
            )}
            {plan.unlinks.length > 0 && (
              <>
                <p className="mt-2 font-medium">And:</p>
                <ul className="list-disc pl-5">
                  {plan.unlinks.map((u) => (
                    <li key={u}>{u}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
          <label className="block text-sm text-gray-700">
            Type <strong className="font-mono">{CONFIRM_WORD}</strong> to confirm
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoFocus
              autoComplete="off"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 font-mono text-sm"
              aria-label={`Type ${CONFIRM_WORD} to confirm`}
            />
          </label>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="danger" disabled={typed !== CONFIRM_WORD || busy}>
              {busy ? 'Deleting…' : `Delete ${label}`}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
};
