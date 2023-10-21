// 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
// 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
const { Configuration, OpenAIApi } = require("openai");
const config = new Configuration({
    apiKey: "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",
})

console.log(Configuration)
const openai = new OpenAIApi(config);


// 圖片數量(一個API最多生成10張圖)
const numberOfImages = 10;
// 圖片大小(單位:px)
const imageSize = "60x60";
// const imageContainer = document.getElementById('imageContainer');

// 設定prompt
var prompt_array = ['Snorlax', 'Charizard', 'Lucario', 'Gengar', 'Umbreon', 'Garchomp', 'Mimikyu', 'Rayquaza', 'Greninja', 'Pikachu'];

for (let i = 1; i <= numberOfImages; i++) {
    openai
        .createImage({
            prompt: prompt_array[i-1],
            n: 1,
            size: imageSize,
        })
        .then((data) => {
            const outputData = data.data.data;
            const image = outputData[0].url;   // image：URL的字串
            const imgElement = document.createElement('img');   // imgElement：在HTML中創建的img
            imgElement.src = image;   // img src設定為圖片網址
            alert(image);
            imgElement.alt = `OpenAI Image ${i}`;   // 若圖片無法顯示時，顯示的替代文字

            // 把圖像放到容器中
            const imageContainer = document.getElementById(`imageContainer${i}`);
            imageContainer.appendChild(imgElement);
        })
        .catch((error) => {
            console.error(`發生錯誤，無法獲取圖像${i}:`, error);
        });
}
