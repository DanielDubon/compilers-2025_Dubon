
import React, { useRef, useEffect } from 'react';
import './EditorSublime.css';

interface EditorProps {
  code: string;
  onChange: (value: string) => void;
}



const keywords = [
  'let', 'const', 'var', 'function', 'if', 'else', 'for', 'while', 'return', 'print',
  'class', 'extends', 'switch', 'case', 'default', 'break', 'continue', 'try', 'catch', 'new', 'void'
];
const booleans = ['true', 'false'];


const numberRegex = /^\d+(\.\d+)?$/;
const keywordRegex = new RegExp(`^(${keywords.join('|')})$`);
const booleanRegex = new RegExp(`^(${booleans.join('|')})$`);

// Para resaltar solo palabras completas
const wordRegex = /[a-zA-Z_][a-zA-Z0-9_]*/g;
const numberWordRegex = /\b\d+(\.\d+)?\b/g;

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


// Tokenizer mejorado: resalta solo palabras completas y no duplica tokens
function highlight(code: string) {
  return code.split(/\n/).map(line => {
    // Comentarios
    const commentIdx = line.indexOf('//');
    let codePart = commentIdx >= 0 ? line.slice(0, commentIdx) : line;
    let commentPart = commentIdx >= 0 ? line.slice(commentIdx) : '';

    // Strings
    let result = '';
    let i = 0;
    while (i < codePart.length) {
      if (codePart[i] === '"' || codePart[i] === "'") {
        const quote = codePart[i];
        let j = i + 1;
        while (j < codePart.length && codePart[j] !== quote) j++;
        j = Math.min(j, codePart.length - 1);
        result += `<span class="token string">${escapeHtml(codePart.slice(i, j + 1))}</span>`;
        i = j + 1;
      } else {
        // Palabras y números
        let match = codePart.slice(i).match(/^\s+/);
        if (match) {
          result += match[0];
          i += match[0].length;
          continue;
        }
        match = codePart.slice(i).match(/^\d+(\.\d+)?/);
        if (match) {
          result += `<span class="token number">${escapeHtml(match[0])}</span>`;
          i += match[0].length;
          continue;
        }
        match = codePart.slice(i).match(/^[a-zA-Z_][a-zA-Z0-9_]*/);
        if (match) {
          const token = match[0];
          if (booleanRegex.test(token)) {
            result += `<span class="token boolean">${escapeHtml(token)}</span>`;
          } else if (keywordRegex.test(token)) {
            result += `<span class="token keyword">${escapeHtml(token)}</span>`;
          } else {
            result += escapeHtml(token);
          }
          i += token.length;
          continue;
        }
        // Otros símbolos
        result += escapeHtml(codePart[i]);
        i++;
      }
    }
    // Agrega comentario si existe
    if (commentPart) {
      result += `<span class="token comment">${escapeHtml(commentPart)}</span>`;
    }
    return result;
  }).join('\n');
}

const Editor: React.FC<EditorProps> = ({ code, onChange }) => {
  const preRef = useRef<HTMLPreElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Line numbers
  const lines = code.split('\n');

  // Scroll sync
  const handleScroll = () => {
    if (preRef.current && textareaRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
    const linesElem = document.querySelector('.editor-sublime-lines');
    if (linesElem && textareaRef.current) {
      linesElem.scrollTop = textareaRef.current.scrollTop;
    }
  };

  return (
    <div className="editor-sublime-container" style={{ display: 'flex', flexDirection: 'row', position: 'relative', minHeight: 260 }}>
      <div className="editor-sublime-lines" style={{ position: 'relative', zIndex: 3 }}>
        {lines.map((_, i) => (
          <span key={i} style={{ display: 'block', height: '1.5em' }}>{i + 1}</span>
        ))}
      </div>
      <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
        <pre
          className="editor-sublime-highlight"
          ref={preRef}
          aria-hidden="true"
          dangerouslySetInnerHTML={{ __html: highlight(code) + (code.endsWith('\n') ? '\n' : '') }}
          style={{ margin: 0 }}
        />
        <textarea
          ref={textareaRef}
          value={code}
          onChange={e => onChange(e.target.value)}
          rows={lines.length}
          spellCheck={false}
          className="editor-sublime-textarea"
          onScroll={handleScroll}
          style={{ margin: 0 }}
        />
      </div>
    </div>
  );
};

export default Editor;