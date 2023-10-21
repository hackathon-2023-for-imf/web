let sectionContentClickCount = 0;
let clickTimer;

// 點擊新聞
function handleSectionContentClick() {
    sectionContentClickCount++;
    clearTimeout(clickTimer);
    clickTimer = setTimeout(() => {
        // 點擊一下：統整大意、文字&聲音輸出、digital life
        if (sectionContentClickCount === 1) {
            alert('Execute .exe file here');
        // 點擊兩下：開啟新聞頁面
        } else if (sectionContentClickCount === 2) {
            window.open('https://www.youtube.com/', '_blank');
        }
        sectionContentClickCount = 0;
    }, 300);
}
