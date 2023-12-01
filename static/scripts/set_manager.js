// --- UUIDv4 generator (thanks to @broofa on StackOverflow)
function uuidv4() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

let MQ = MathQuill.getInterface(2);

// --- Autosave

let queue = [];
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

$(document).ready(function() {
    $('#options input, #options textarea').on("keyup", function (event) {
        queue.push([event.target.name, $(event.target).val()]);
    });
    $('#options select').on("change", function (event) {
        queue.push([event.target.name, $(event.target).val()]);
    });
    $('#options input[type=checkbox]').on("change", function (event) {
        queue.push([event.target.name, $(event.target).is(":checked")]);
    })
});

function save(exit=false, manual=false) {
    // Allows for waiting until the save succeeds
    let finished_set = false;
    let finished_cards = false;
    let sent_data = false;
    let errors = false;
    if (!$.isEmptyObject(card_queue)) {
        // for (let card_id in card_queue) {
        let data = {...card_queue};
        data['set_id'] = set_id;
            // data['card_id'] = card_id
        //     socket.emit("update_card", data, (response) => {
        //         if (response === 'success') {
        //             finished_cards = true;
        //             sent_data = true;
        //             card_queue = {};
        //         }
        //         else {
        //             errors = true;
        //         }
        //     });
        // }
        socket.emit("update_cards", data, (response) => {
            if (response === 'success') {
                finished_cards = true;
                sent_data = true;
                card_queue = {};
            }
        });
    }
    else { finished_cards = true; }
    let interval
    interval = setInterval(function save_process() {
        if (errors) {
            window.alert('There was an issue saving this set. Try again, or make a copy of your work and reload the page.')
            clearInterval(interval);
        }
        else if (finished_cards) {
            finished_cards = false;
            if (!$.isEmptyObject(queue)) {
            let data = {...queue}  // Copy the queue
            socket.emit("update_set", [set_id, data], (response) => {
                if (response === 'success') {
                    finished_set = true;
                    sent_data = true;
                    queue = [];
                }
                else {
                    errors = true;
                }
            });
            }
            else { finished_set = true; }
        }
        else if (finished_set) {
            if (exit) {
                window.location.href = '..';
            }
            clearInterval(interval);
            if (sent_data || manual) {
                showSaveDialog();
            }
        }
        return save_process
    }(), 200)
}

setInterval(function() {
    if (autosave) {
        save();
    }
}, 10000)

// ---x

// --- Card operations

function getCardData(card_id) {
    let cardObj = $(`.card[data-card-id="${card_id}"]`);
    let cardInputObjs = cardObj.find(".card-text, .math-field");
    let output = {};
    let result;
    cardInputObjs.each(function(i) {
        result = ""
        if (cardInputObjs.eq(i).hasClass("math-field")) {
            result = "@@MQ@@" + MQ.MathField(cardInputObjs.get(i)).latex();
        }
        else {
            result = cardInputObjs.eq(i).val();
        }

        if (i === 0) {
            output['front'] = result;
        }
        else {
            output['back'] = result;
        }
    });
    return output;
}

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
    $(`.card[data-card-id="${card_id}"]`).remove();
    queue.push(['delete_card', card_id]);
}

function add_card() {
    let card_id = uuidv4();
    $(`<div class="card" data-card-id="${card_id}">
            <div class="card-header">
                <p><span class="material-symbols-outlined drag-handle">drag_handle</span></p>
                <p><span class="material-symbols-outlined delete-btn">delete</span></p>
            </div>
            <div class="card-body">
                <div class="card-content">
                    <form>
                         <label>
                            Front
                            <input type="text" autocomplete="off" class="card-text" value="">
                            <a class="math-toggle" title="Write a math equation"><span class="material-symbols-outlined">function</span></a>
                        </label>
                        <label>
                            Back&nbsp;
                            <input type="text" autocomplete="off" class="card-text" value="">
                            <a class="math-toggle"><span class="material-symbols-outlined">function</span></a>
                        </label>
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
    ).insertBefore('#bottom');
    $(`.card[data-card-id='${card_id}']`)[0].scrollIntoView({
        behavior: 'smooth'
    });
    $(`.card[data-card-id='${card_id}'] input`)[0].focus();
    // queue.push(['new_card', card_id]);
}

function update_card(card_id, front, back) {
    card_queue[card_id] = {"front": front, "back": back};
}

function change_position(cardpos_initial, cardpos_final) {
    if (cardpos_initial !== cardpos_final) {
        queue.push(['change_position', {
            "initial": cardpos_initial,
            "final": cardpos_final
        }])
    }
}

// ---x

// --- Event listeners

$(document).ready(function() {
    // -- Buttons
    $("#card-container").on("click", ".card .delete-btn", function (event) {
        let card_id = $(event.target).parents().eq(2).attr('data-card-id');
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
    $("#card-container").on("keyup", ".card input, .card .math-field", function (event) {
        let card_id = $(this).parents().eq(4).attr('data-card-id');
        if (!card_id.startsWith('temp')) {
            let data = getCardData(card_id);
            update_card(card_id, data['front'], data['back']);
        }
    });
    $("#card-container").on("click", ".card .math-toggle", function (event) {
        if ($(this).hasClass("active")) {
            $(this).removeClass("active");
            let inputField = $(this).parents().eq(0).find('.math-field').eq(0);
            convert_to_regular_field(inputField);
        }
        else {
            $(this).addClass("active");
            let inputField = $(this).parents().eq(0).find('input').eq(0);
            make_math_field(inputField);
        }
        let card_id = $(this).parents().eq(4).attr('data-card-id');
        if (!card_id.startsWith('temp')) {
            let data = getCardData(card_id);
            update_card(card_id, data['front'], data['back']);
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
        let card_id = $(event.target).parents().eq(3).attr('data-card-id');
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

// ---x

// --- Convert as required to MathQuill
$(document).ready(function() {
    let to_convert = $(".convertMQ");
    to_convert.each(function (i) {
        make_math_field(to_convert.eq(i));
    })
});
// ---x