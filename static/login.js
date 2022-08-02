function OnLoaded() {
    var data = document.getElementById("data-tag");
    if (data.value == "ERR") {
        var block = document.getElementById("error-head");
        block.style.display = "block"
    }
}

function HideError() {
    var block = document.getElementById("error-head");
    block.style.display = "none"
}
