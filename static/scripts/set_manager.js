// --- Autosave

let queue = {}
let card_queue = {}
let set_id = window.location.pathname.split('/')[2]

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

function save() {
    if (!$.isEmptyObject(queue)) {
        let data = {...queue}  // Copy the queue
        data['set_id'] = set_id;
        socket.emit("update_set", data);
        queue = {};
    }
    if (!$.isEmptyObject(card_queue)) {
        for (let card_id in card_queue) {
            let data = {...card_queue[card_id]};
            data['set_id'] = set_id;
            data['card_id'] = card_id
            socket.emit("update_card", data);
            card_queue = {};
        }
    }
}

setInterval(function() {
    save();
}, 5000)

// ---x

// --- Card operations

function delete_card(card_id) {
    socket.emit("delete_card", {"set_id": set_id, "card_id": card_id}, (response) => {
        if (response === 'success') {
            $(`.card[data-card-id="${card_id}"]`).remove();
        }
    });
}

function add_card() {
    socket.emit("new_card", {"set_id": set_id}, (response) => {
        $("#card-container").append(
            `<div class="card" data-card-id="${response['id']}">
                <div class="card-header">
                    <p><span class="material-symbols-outlined drag-handle">drag_handle</span></p>
                    <p><span class="material-symbols-outlined delete-btn">delete</span></p>
                </div>
                <div class="card-body">
                    <div class="card-content">
                        <form>
                            <label>Front<input type="text" class="card-text" value="${response['front']}"></label>
                            <label>Back&nbsp;<input type="text" class="card-text" value="${response['back']}"></label>
                        </form>
                    </div>
                    <div class="card-image">
                        <p class="cutout desktop">+</p>
                        <p class="cutout mobile">+ Image</p>
                    </div>
                </div>
            </div>`
        );
        $(`.card[data-card-id='${response['id']}']`).insertBefore('#new_card');
    });
}

function update_card(card_id, front, back) {
    card_queue[card_id] = {"front": front, "back": back};
}

// ---x

// --- Event listeners

$(document).ready(function() {
    // -- Buttons
    $("#new_card").on("click", function() {
        add_card();
    });
    $("#card-container").on("click", ".card .delete-btn", function (event) {
        let card_id = $(event.target).parents().eq(2).data('card-id');
        delete_card(card_id);
    });
    $('#delete-set').on("click", function (event) {
        const response = confirm("Do you want to delete this set? This action CANNOT BE UNDONE!")
        if (response) {
            window.location.href = '../delete'
        }
    })
    // --x
    // -- Card inputs
    $("#card-container").on("change", ".card input", function (event) {
        let card_id = $(event.target).parents().eq(4).data('card-id');
        let form = $(event.target).parents().eq(1);
        let front = form.find('input').eq(0).val();
        let back = form.find('input').eq(1).val();
        update_card(card_id, front, back);
    })
    // --
})

// ---x
