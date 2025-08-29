export async function compileCode(code: string): Promise<{ output: string, errors: string }> {
    const response = await fetch('http://localhost:5000/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
    });
    return await response.json();
}