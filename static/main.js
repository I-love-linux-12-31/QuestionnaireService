function addCopyTextHandler(element, text) {
    element.addEventListener('click', async () => {
            try {
              await navigator.clipboard.writeText(text);
            } catch (error) {
              console.error('Text copping error:', error);
              fallbackCopyTextToClipboard(text);
            }
          });
}


function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
    } catch (err) {
        console.error('Text copping error(fallback):', err);
    }
    document.body.removeChild(textArea);
}
