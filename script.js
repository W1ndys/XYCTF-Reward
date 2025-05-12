document.getElementById('generateBtn').addEventListener('click', async () => {
    const nameInput = document.getElementById('nameInput');
    const imagesContainer = document.getElementById('imagesContainer');
    const loadingIndicator = document.getElementById('loading');
    const resultArea = document.getElementById('resultArea');

    const names = nameInput.value.split(/\s+/).filter(name => name.trim() !== ''); // Split by whitespace and filter empty

    if (names.length === 0) {
        alert('请输入至少一个名字！');
        return;
    }

    imagesContainer.innerHTML = ''; // Clear previous results
    loadingIndicator.classList.remove('hidden');
    resultArea.classList.remove('hidden'); // Show result area section title

    try {
        // We will generate images one by one to avoid potential timeouts
        // and large requests/responses if many names are entered.
        for (const name of names) {
            console.log(`Generating image for: ${name}`);
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: name }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`生成 '${name}' 失败: ${response.status} ${errorText}`);
            }

            // Get image blob and create a URL for display/download
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);

            // Create elements to display the image and download link
            const imageDiv = document.createElement('div');
            imageDiv.classList.add('result-image');

            const img = document.createElement('img');
            img.src = imageUrl;
            img.alt = `Generated image for ${name}`;

            const downloadLink = document.createElement('a');
            downloadLink.href = imageUrl;
            downloadLink.download = `${name}.png`; // Set filename for download
            downloadLink.textContent = `下载 ${name}.png`;

            imageDiv.appendChild(img);
            imageDiv.appendChild(downloadLink);
            imagesContainer.appendChild(imageDiv);
        }

    } catch (error) {
        console.error('生成过程中出错:', error);
        imagesContainer.innerHTML = `<p style="color: red;">生成失败：${error.message}</p>`;
    } finally {
        loadingIndicator.classList.add('hidden');
    }
}); 