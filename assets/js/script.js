var exampleSocket = null;
var state = "email";

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for(var i=0; i<ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1);
        if (c.indexOf(name) == 0) {
            cval = c.substring(name.length,c.length);
            return cval;
        }
    }
    return null;
}

function submitcontent() {
    if (exampleSocket == null) {
        exampleSocket = new WebSocket("ws://localhost:8888/signup");
        exampleSocket.onopen = function(event) {
            var val = document.getElementById('content').value;
            var msg = {
                type: 'email',
                _xsrf: getCookie('_xsrf'),
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
                _xsrf: getCookie('_xsrf'),
                eotp: val
            };
            state = "ssms";
            break;
            case "ssms":
            var msg = {
                type: 'addr',
                _xsrf: getCookie('_xsrf'),
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
