let boxes = [];
let img = new Image();
const canvas = document.getElementById("canvas");

canvas.addEventListener("click",async function(event) {
    const x = event.offsetX
    const y = event.offsetY

    console.log("Clicked at:", x,y);

    for (let box of boxes){
        if(
            x>= box.x &&
            x<= box.x + box.w &&
            y>= box.y &&
            y<= box.y + box.h
        ){
            console.log("clicked text:",box.text);

            let newText = prompt("Enter new text:");
        }
    }
    
})