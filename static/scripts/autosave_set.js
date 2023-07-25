let queue = {}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

var socket = io.connect(location.protocol + "//" + document.domain + ':' + location.port);

$(document).ready(function() {
    $('#options input, #options textarea').on("keyup", function (event) {
        queue[event.target.id] = $(event.target).val();
    });
    $('#options select').on("change", function (event) {
        queue[event.target.id] = $(event.target).val();
    })
});

setInterval(function() {
    if (!$.isEmptyObject(queue)) {
            let data = {...queue}  // Copy the queue
            data['set_id'] = window.location.pathname.split('/')[2]
            socket.emit("update_set", data);
            queue = {}
        }
}, 5000)
