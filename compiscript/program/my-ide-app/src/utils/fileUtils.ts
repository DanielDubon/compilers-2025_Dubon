import { saveAs } from 'file-saver';

export const saveFile = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    saveAs(blob, filename);
};

export const loadFile = async (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (event) => {
            if (event.target) {
                resolve(event.target.result as string);
            }
        };
        reader.onerror = (error) => reject(error);
        reader.readAsText(file);
    });
};