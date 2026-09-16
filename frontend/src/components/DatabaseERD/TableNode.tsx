import { Handle, Position } from '@xyflow/react';

type Column = {
  name: string;
  label?: string; 
  type: string;
};

type TableNodeProps = {
  data: {
    label: string;
    schema: string;
    columns: Column[];
  };
};

export default function TableNode({ data }: TableNodeProps) {
  return (
    <div className="bg-white rounded-md shadow-lg border border-gray-200 min-w-[200px] overflow-hidden font-sans">
      <Handle className="w-2 h-2 !bg-blue-500" position={Position.Left} type="target"/>
      
      <div className="bg-slate-800 text-white px-3 py-2 text-sm font-semibold flex justify-between items-center">
        <span>{data.label}</span>
        <span className="text-xs text-slate-400 font-mono ml-4">{data.schema}</span>
      </div>

      <div className="flex flex-col p-1">
        {data.columns?.map((col, idx) => (
          <div key={idx} className="flex justify-between items-center px-2 py-1 border-b border-gray-100 last:border-0 text-xs">
            <span className="font-medium text-gray-700">{col.label || col.name}</span>
            <span className="text-gray-400 font-mono ml-4">{col.type}</span>
          </div>
        ))}
      </div>

      <Handle className="w-2 h-2 !bg-blue-500" position={Position.Right} type="source"/>
    </div>
  );
}