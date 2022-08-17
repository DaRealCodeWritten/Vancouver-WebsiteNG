let icao = document.getElementsByClassName("icao")[0];
icao.addEventListener('keypress', function (event) {
    let regex = new RegExp("^[a-zA-Z]");
    let key = String.fromCharCode(!event.charCode ? event.which : event.charCode);
    if (!regex.test(key)) {
        event.preventDefault();
        let button = document.getElementsByClassName("submit")[0];
        button.disabled = true;
        console.log("Bad");
        return false;
    }
    else {
        let button = document.getElementsByClassName("submit")[0];
        button.disabled = false;
        console.log("Good");
        return true;
    }
});