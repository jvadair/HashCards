// --- UUIDv4 generator (thanks to @broofa on StackOverflow)
function uuidv4() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

// --- Autosave  TODO: Make everything a single queue and socket listener, and then create multiple functions in app.py

let queue = {};
let card_queue = {};
let set_id = window.location.pathname.split('/')[2];
let card_being_dragged = "";
let cardpos_initial = 0;
let cardpos_final = 0;
let autosave = true;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

const delay = ms => new Promise(res => setTimeout(res, ms));
const showSaveDialog = async () => {
    $("#save-indicator").addClass("animate");
    await delay(3000);
    $("#save-indicator").removeClass("animate");
};

let socket;
$(document).ready(function() {
    $('#options input, #options textarea').on("keyup", function (event) {
        queue[event.target.name] = $(event.target).val();
    });
    $('#options select').on("change", function (event) {
        queue[event.target.name] = $(event.target).val();
    });
    $('#options input[type=checkbox]').on("change", function (event) {
        queue[event.target.name] = $(event.target).is(":checked");
    })
    socket = io.connect(location.protocol + "//" + document.domain + ':' + location.port);
});

function save(exit=false, manual=false) {
    // Allows for waiting until the save succeeds
    let finished_set = false;
    let finished_cards = false;
    let sent_data = false;
    let errors = false;
    if (!$.isEmptyObject(queue)) {
        let data = {...queue}  // Copy the queue
        data['set_id'] = set_id;
        socket.emit("update_set", data, (response) => {
            if (response === 'success') {
                finished_set = true;
                sent_data = true;
                queue = {};
            }
            else {
                errors = true;
            }
        });
    }
    else { finished_set = true; }
    if (!$.isEmptyObject(card_queue)) {
        for (let card_id in card_queue) {
            let data = {...card_queue[card_id]};
            data['set_id'] = set_id;
            data['card_id'] = card_id
            socket.emit("update_card", data, (response) => {
                if (response === 'success') {
                    finished_cards = true;
                    sent_data = true;
                    card_queue = {};
                }
                else {
                    errors = true;
                }
            });
        }
    }
    else { finished_cards = true; }
    let interval
    interval = setInterval(function () {
        if (errors) {
            window.alert('There was an issue saving this set. Try again, or make a copy of your work and reload the page.')
            clearInterval(interval);
        }
        else if (finished_set && finished_cards) {
            if (exit) {
                window.location.href = '..';
            }
            clearInterval(interval);
            if (sent_data || manual) {
                showSaveDialog();
            }
        }
    }, 200)
}

setInterval(function() {
    if (autosave) {
        save();
    }
}, 10000)

// ---x

// --- Card operations

function delete_image(e) {
    let card_id = $(e).parents().eq(2).data('card-id');
    socket.emit("remove_image", {"set_id": set_id, "card_id": card_id}, (response) => {
        if (response !== 401) {
            $(e).removeClass('active');
            $(e).parents().eq(0).css("background-image", "none");
            $(e).parents().eq(1).find("label").removeClass('hidden');
        }
        else {
            window.alert("Couldn't delete image - please sign in and try again.")
        }
    });
}

function delete_card(card_id) {
    $(`.card[data-card-id="${card_id}"]`).hide();
    socket.emit("delete_card", {"set_id": set_id, "card_id": card_id}, (response) => {
        if (response === 'success') {
            $(`.card[data-card-id="${card_id}"]`).remove();
        }
        else {
           $(`.card[data-card-id="${card_id}"]`).show();
           window.alert('Failed to delete card - try again or attempt to save and reload');
        }
    });
}

function add_card() {
    let temporary_id = 'temp' + uuidv4();
    $("#card-container").append(
        `<div class="card" data-card-id="${temporary_id}">
            <div class="card-header">
                <p><span class="material-symbols-outlined drag-handle">drag_handle</span></p>
                <p><span class="material-symbols-outlined delete-btn">delete</span></p>
            </div>
            <div class="card-body">
                <div class="card-content">
                    <form>
                        <label>Front<input type="text" class="card-text card-text-front" value=""></label>
                        <label>Back&nbsp;<input type="text" class="card-text card-text-back" value=""></label>
                    </form>
                </div>
                <form class="card-image">
                    <label class="cutout desktop">
                        <input type="file" class="image-upload" name="image" style="display: none" accept="image/jpeg, image/png, image/bmp, image/gif, image/webp"></input>
                        +
                    </label>
                    <label class="cutout mobile">
                        <input type="file" class="image-upload" name="image" style="display: none" accept="image/jpeg, image/png, image/bmp, image/gif, image/webp"></input>
                        + Image
                    </label>
                    <div class="image_added_overlay" onclick="delete_image(this);">
                        <span class="material-symbols-outlined">delete</span>
                    </div>
                </form>
            </div>
        </div>`
    );
    $(`.card[data-card-id='${temporary_id}']`).insertBefore('#new_card');
    $(`.card[data-card-id='${temporary_id}']`)[0].scrollIntoView({
        behavior: 'smooth'
    });
    $(`.card[data-card-id='${temporary_id}'] input`)[0].focus();
    socket.emit("new_card", {"set_id": set_id}, (response) => {
        if (response !== 401) {
            $(`.card[data-card-id=${temporary_id}] .card-text-front`).val(response['front']);
            $(`.card[data-card-id=${temporary_id}] .card-text-back`).val(response['back']);
            $(`.card[data-card-id=${temporary_id}]`).attr('data-card-id', response['id']);
        }
        else {
            $(`.card[data-card-id=${temporary_id}]`).remove();
            window.alert("Couldn't add a new card - try again or attempt to save and reload.");
        }
    });
}

function update_card(card_id, front, back) {
    card_queue[card_id] = {"front": front, "back": back};
}

function change_position(cardpos_initial, cardpos_final) {
    if (cardpos_initial !== cardpos_final) {
        socket.emit("change_position", {
            "set_id": set_id,
            "initial": cardpos_initial,
            "final": cardpos_final
        });
    }
}

// ---x

// --- Event listeners

$(document).ready(function() {
    // -- Buttons
    $("#card-container").on("click", ".card .delete-btn", function (event) {
        let card_id = $(event.target).parents().eq(2).data('card-id');
        delete_card(card_id);
    });
    $('#delete-set').on("click", function (event) {
        const response = confirm("Do you want to delete this set? This action CANNOT BE UNDONE!")
        if (response) {
            fetch('/set/' + set_id, {
                method: 'DELETE',
                credentials: 'include'
            }).then(r => {
                if (r.status !== 401) {
                    window.location.href = '/sets';
                }
            });
        }
    });
    // $('#autosave-toggle').on("click", function (event) {
    //     autosave = $('#autosave-toggle').is(":checked");
    //     save();
    // });
    // --x
    // -- Card inputs
    $("#card-container").on("keyup", ".card input", function (event) {
        let card_id = $(event.target).parents().eq(4).data('card-id');
        if (!card_id.startsWith('temp')) {
            let form = $(event.target).parents().eq(1);
            let front = form.find('input').eq(0).val();
            let back = form.find('input').eq(1).val();
            update_card(card_id, front, back);
        }
    });
    // --
    // -- Dragging
    $("#card-container").on("mousedown", ".card .drag-handle", function (event) {
        card_being_dragged = $(event.target).parents().eq(2);
        cardpos_initial = $(event.target).parents().eq(2).index();
    });
    // -- Image uploading
    $("#card-container").on("change", "input.image-upload", function(event) {
        let file = $(event.target).prop('files')[0];
        let card_id = $(event.target).parents().eq(3).data('card-id');
        socket.emit("add_image", {"set_id": set_id, "card_id": card_id, "file": file, "filename": $(event.target).val()}, (response) => {
        if (response !== 401) {
            $(event.target).parents().eq(0).addClass('hidden');
            $(event.target).parents().eq(1).css("background-image", `url('/static/images/card_images/${response}.png')`);
            $(event.target).parents().eq(1).find(".image_added_overlay").eq(0).addClass('active');
        }
        else {
            window.alert("Couldn't add image - please sign in and try again.")
        }
        });
    })
})

// ---x

// --- Card dragging

$(document).ready(function() {
    $("#card-container").sortable({
        axis: "y",
        containment: "#card-container",
        cursor: "grabbing",
        handle: ".drag-handle",
        stop: function (event) {
            cardpos_final = card_being_dragged.index();
            change_position(cardpos_initial, cardpos_final);
        }
    });
   $('#visibility').change(function() {
        if ($('#visibility').val() === 'private') {
            $('#visibility').css('color','#ff6b79');
        }
        else if ($('#visibility').val() === 'unlisted') {
            $('#visibility').css('color','#eba050');
        }
        else {
            $('#visibility').css('color','#43AA8B');
        }
   });
});