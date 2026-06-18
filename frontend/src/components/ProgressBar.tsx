interface ProgressBarProps {
  steps: string[];
  currentStep: number;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ steps, currentStep }) => (
  <div className="mb-8">
    <div className="flex gap-2">
      {steps.map((label, idx) => (
        <div
          key={label}
          className={`flex-1 h-1.5 rounded ${idx <= currentStep ? 'bg-blue-600' : 'bg-gray-300'}`}
        />
      ))}
    </div>
    <div className="text-xs text-gray-600 mt-2">
      Step {Math.min(currentStep + 1, steps.length)} of {steps.length}: {steps[currentStep]}
    </div>
  </div>
);
