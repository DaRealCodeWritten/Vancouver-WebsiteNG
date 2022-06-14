function isSure() {
    var on = document.getElementById("delete-user").value;
    if (on === "True") {
        document.getElementById("delete-sure").style.display = "none";
        document.getElementById("delete-user").value = "False";
        console.log("Toggle False");
    }
    else {
        document.getElementById("delete-sure").style.display = "block";
        document.getElementById("delete-user").value = "True";
        console.log("Toggle True");
    }
}