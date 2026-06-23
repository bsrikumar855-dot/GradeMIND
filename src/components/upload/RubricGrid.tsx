import React from 'react';
import { RubricCriterion } from './types';
import { Sparkles, Trash2, Plus, GripVertical } from 'lucide-react';
import { cn } from '@/utils/cn';

interface RubricGridProps {
  rubric: RubricCriterion[];
  onChange: (rubric: RubricCriterion[]) => void;
}

export function RubricGrid({ rubric, onChange }: RubricGridProps) {
  const handleAutoGenerate = () => {
    // Mock auto-generate behavior
    const mockRubric: RubricCriterion[] = [
      { id: '1', label: 'Clear thesis statement and introduction', marks: 10, required: true },
      { id: '2', label: 'Logical flow and paragraph structure', marks: 15, required: true },
      { id: '3', label: 'Evidence and citations provided', marks: 20, required: false },
      { id: '4', label: 'Grammar, spelling, and punctuation', marks: 5, required: true },
    ];
    onChange(mockRubric);
  };

  const handleUpdate = (id: string, field: keyof RubricCriterion, value: string | number | boolean) => {
    onChange(rubric.map(item => item.id === id ? { ...item, [field]: value } : item));
  };

  const handleRemove = (id: string) => {
    onChange(rubric.filter(item => item.id !== id));
  };

  const handleAdd = () => {
    onChange([...rubric, { id: Math.random().toString(36).substr(2, 9), label: '', marks: 0, required: false }]);
  };

  const totalMarks = rubric.reduce((sum, item) => sum + (Number(item.marks) || 0), 0);

  return (
    <div className="w-full h-full flex-1 p-10 flex flex-col gap-8 min-h-[500px]">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-gray-100 pb-6">
        <div>
          <h2 className="text-3xl font-bold text-brand-dark mb-2">Rubric Intelligence Builder</h2>
          <p className="text-gray-500 text-base">Define grading criteria or let Llama 3.3 generate it from your Answer Key.</p>
        </div>
        <button
          onClick={handleAutoGenerate}
          className="flex items-center gap-2.5 bg-brand-accent/10 hover:bg-brand-accent/20 text-brand-accent px-5 py-3 rounded-xl font-bold transition-all whitespace-nowrap text-base"
        >
          <Sparkles className="w-5 h-5" />
          Auto-Generate via Llama 3.3
        </button>
      </div>

      <div className="flex-1 overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b-2 border-brand-surface/50">
              <th className="pb-4 w-10"></th>
              <th className="pb-4 text-sm font-semibold text-gray-500 uppercase tracking-wider">Criterion Label</th>
              <th className="pb-4 text-sm font-semibold text-gray-500 uppercase tracking-wider w-28">Marks</th>
              <th className="pb-4 text-sm font-semibold text-gray-500 uppercase tracking-wider w-36 text-center">Required</th>
              <th className="pb-4 w-14"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {rubric.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-16 text-center text-gray-400 text-lg">
                  No criteria defined. Click &quot;Add Row&quot; or auto-generate.
                </td>
              </tr>
            ) : (
              rubric.map((item) => (
                <tr key={item.id} className="group hover:bg-gray-50/50 transition-colors">
                  <td className="py-4">
                    <GripVertical className="w-5 h-5 text-gray-300 cursor-grab" />
                  </td>
                  <td className="py-4 pr-4">
                    <input
                      type="text"
                      value={item.label}
                      onChange={(e) => handleUpdate(item.id, 'label', e.target.value)}
                      placeholder="e.g., Accuracy of calculation"
                      className="w-full bg-transparent border border-transparent hover:border-gray-200 focus:border-brand-primary focus:bg-white rounded-lg px-4 py-3 text-brand-dark focus:outline-none transition-all font-mono text-base"
                    />
                  </td>
                  <td className="py-4 pr-4">
                    <input
                      type="number"
                      value={item.marks || ''}
                      onChange={(e) => handleUpdate(item.id, 'marks', Number(e.target.value))}
                      min="0"
                      className="w-24 bg-transparent border border-gray-200 focus:border-brand-primary focus:bg-white rounded-lg px-4 py-3 text-brand-dark focus:outline-none transition-all font-mono text-base"
                    />
                  </td>
                  <td className="py-4 text-center">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input 
                        type="checkbox" 
                        className="sr-only peer" 
                        checked={item.required}
                        onChange={(e) => handleUpdate(item.id, 'required', e.target.checked)}
                      />
                      <div className="w-12 h-7 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[3px] after:left-[3px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-[22px] after:w-[22px] after:transition-all peer-checked:bg-green-500"></div>
                    </label>
                  </td>
                  <td className="py-4 text-right">
                    <button
                      onClick={() => handleRemove(item.id)}
                      className="text-gray-300 hover:text-red-500 p-2.5 rounded-lg hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between items-center pt-5 border-t border-gray-100">
        <button
          onClick={handleAdd}
          className="flex items-center gap-2.5 text-brand-dark font-semibold hover:text-brand-primary transition-colors text-base"
        >
          <Plus className="w-5 h-5" />
          Add Criterion
        </button>
        <div className="text-brand-dark font-bold text-lg">
          Total Marks Allocated: <span className={cn("text-xl ml-2", totalMarks > 0 ? "text-green-600" : "text-gray-400")}>{totalMarks}</span>
        </div>
      </div>
    </div>
  );
}
