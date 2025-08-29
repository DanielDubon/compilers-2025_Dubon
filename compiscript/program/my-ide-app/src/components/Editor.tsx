import React from 'react';

interface EditorProps {
  code: string;
  onChange: (value: string) => void;
}

const Editor: React.FC<EditorProps> = ({ code, onChange }) => (
  <textarea
    value={code}
    onChange={e => onChange(e.target.value)}
    rows={12}
    cols={60}
    style={{ fontFamily: 'monospace', fontSize: '16px', width: '100%', marginBottom: '16px' }}
  />
);

export default Editor;