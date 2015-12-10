var exampleSocket = null;
var state = "email";

function submitcontent() {
    if (exampleSocket == null) {
        exampleSocket = new WebSocket("ws://localhost:8888/signup");
        exampleSocket.onopen = function(event) {
            var val = document.getElementById('content').value;
            var msg = {
                type: 'email',
                email: val
            };
            exampleSocket.send(JSON.stringify(msg));
            state = "eotp";
        }
        exampleSocket.onmessage = handlemessage;
        exampleSocket.onclose = handleclose;
    } else {
        var val = document.getElementById('content').value;
        switch(state) {
            case "eotp":
            var msg = {
                type: 'eotp',
                eotp: val
            };
            state = "ssms";
            break;
            case "ssms":
            var msg = {
                type: 'addr',
                addr: val
            };
            state = "done";
            break;
        }
        exampleSocket.send(JSON.stringify(msg));
    }
}

function handlemessage(event) {
    var msg = JSON.parse(event.data);
    switch(msg.type) {
        case "eotp":
            document.getElementById('modalhead').innerHTML = msg.modalhead;
            document.getElementById('innermodal').innerHTML = msg.innermodal;
        break;
        case "ssms":
            document.getElementById('modalhead').innerHTML = msg.modalhead;
            document.getElementById('innermodal').innerHTML = msg.innermodal;
        break;
        case "addr":
            document.getElementById('modalhead').innerHTML = msg.modalhead;
            document.getElementById('innermodal').innerHTML = msg.innermodal;
        break;
    }
}

function handleclose(event) {
    if (event.code != 1003 && state == "done") {
        alert('Signup Complete, Thanks');
    } else if (event.code != 1003) {
        alert('Unknown Error Occured, Sorry :-(')
    } else {
        alert('Error: ' + event.reason);
    }
    window.location.reload();
}
