import React from 'react';

interface ToolbarProps {
  onCompile: () => void;
}

const Toolbar: React.FC<ToolbarProps> = ({ onCompile }) => (
  <div style={{ marginBottom: '10px' }}>
    <button onClick={onCompile}>Compilar</button>
  </div>
);

export default Toolbar;