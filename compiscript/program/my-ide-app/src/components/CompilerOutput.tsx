import React from 'react';

interface CompilerOutputProps {
  output: string;
  errors: string;
}

const CompilerOutput: React.FC<CompilerOutputProps> = ({ output, errors }) => (
  <div style={{
    marginTop: '20px',
    background: '#232629',
    padding: '10px',
    borderRadius: '4px',
    minHeight: '60px',
    color: '#f8f8f2',
    border: '1px solid #444'
  }}>
    <h3>Salida del compilador:</h3>
    {output && <pre>{output}</pre>}
    {errors && (
      <pre style={{ color: 'red' }}>
        {errors}
      </pre>
    )}
  </div>
);

export default CompilerOutput;