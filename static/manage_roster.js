function certs2HTML() {
    let certs = document.getElementById("certs-data-raw").value.toString().split("");
    let cells = document.getElementsByClassName("cell");
    for (let cell of cells) {
        cell.style.backgroundColor = "white";
    }
    if (certs.length == 1) {
        certs = [0, 0, 0, 0, 0, 0];
    }
    let htmls = [
        document.getElementById("del-cert"),
        document.getElementById("gnd-cert"),
        document.getElementById("twr-cert"),
        document.getElementById("dep-cert"),
        document.getElementById("app-cert"),
        document.getElementById("ctr-cert")
    ];
    for (let i = 0; i < certs.length; i++) {
        let cert = certs[i];
        let obj = htmls[i];
        switch(cert.toString()) {
            case "0":
                obj.style.backgroundColor = "white";
                obj.innerText = "Not Certified";
                obj.style.color = "black";
                break;
            case "1":
                obj.style.backgroundColor = "blue";
                obj.innerText = "In Training";
                obj.style.color = "black";
                break;
            case "2":
                obj.style.backgroundColor = "orange";
                obj.innerText = "Solo Certified";
                obj.style.color = "black";
                break;
            case "3":
                obj.style.backgroundColor = "green";
                obj.innerText = "Certified";
                obj.style.color = "black";
                break;
        }
    }
}

function rawToPretty() {
    let visitor = document.getElementById("visitor-data-raw");
    let viselement = document.getElementById("visitor");
    switch(visitor.value.toString()) {
        case "0":
            viselement.innerText = "No";
            break;
        case "1":
            viselement.innerText = "Yes";
            break;
    }
    let rating = document.getElementById("rating-data-raw");
    let ratelement = document.getElementById("rating");
    switch(rating.value.toString()) {
        case "1":
            ratelement.innerText = "Observer";
            break;
        case "2":
            ratelement.innerText = "Student 1";
            break;
        case "3":
            ratelement.innerText = "Student 2";
            break;
        case "4":
            ratelement.innerText = "Student 3";
            break;
        case "5":
            ratelement.innerText = "Controller 1";
            break;
        case "7":
            ratelement.innerText = "Controller 3";
            break;
        case "8":
            ratelement.innerText = "Instructor 1";
            break;
        case "10":
            ratelement.innerText = "Instructor 3";
            break;
        case "11":
            ratelement.innerText = "Supervisor";
            break;
        case "12":
            ratelement.innerText = "Administrator";
            break;
    }
}

function switchThis(toswitch) {
    let modswitch = toswitch + "-DIV";
    let tobutton = toswitch + "-BTN";
    let button = document.getElementById(tobutton);
    button.disabled = true;
    let element = document.getElementById(modswitch);
    let others = [
        document.getElementById("DEL-DIV"),
        document.getElementById("GND-DIV"),
        document.getElementById("TWR-DIV"),
        document.getElementById("DEP-DIV"),
        document.getElementById("APP-DIV"),
        document.getElementById("CTR-DIV")
    ];
    let btns = [
        document.getElementById("DEL-BTN"),
        document.getElementById("GND-BTN"),
        document.getElementById("TWR-BTN"),
        document.getElementById("DEP-BTN"),
        document.getElementById("APP-BTN"),
        document.getElementById("CTR-BTN")
    ];
    for (let i = 0; i < others.length; i++) {
        let other = others[i];
        let btn = btns[i];
        if (other != element) {
            other.style.display = "none";
            btn.disabled = false;
        }
    }
    if (element == null) {
        throw TypeError("Element not found")
    }
    else {
        switch(element.style.display) {
            case "none":
                element.style.display = "block";
                break;
            case "block":
                element.style.display = "none";
                break;
            case "":
                element.style.display = "block";
                break;
        }
    }
}