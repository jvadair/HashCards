let set_id = window.location.pathname.split('/')[2];
let MQ = MathQuill.getInterface(2);

function get_card_from_table(n) {
    let front = $(`table tr:nth-of-type(${n}) td:nth-of-type(2) div`).html();
    let back = $(`table tr:nth-of-type(${n}) td:nth-of-type(3)`).html();
    return [front, back];
}

function update_card() {
    $('#card').replaceWith("<div id='card'></div>")  // Replacing the card is the only way to avoid the animation
    $('#card').append(`<div class='front'>${current_card[0]}</div>`.replace("<p", "<h2").replace("</p>", "</h2>"))
    $('#card').append(`<div class='back'><h2>${current_card[1]}</h2></div>`)
    $('#card').flip({
        trigger: 'click'
    });
}

function update_arrows() {
    let locations = ['#card-viewer', '#mobile-arrows']
    for (let location of locations) {
        if (current_card_number == 1) {
            if ($(`${location} #arrow-back`).hasClass('active')) {
                $(`${location} #arrow-back`).removeClass('active')
            }
            if (!$(`${location} #arrow-forward`).hasClass('active') && total_cards != 1) {
                $(`${location} #arrow-forward`).addClass('active')
            }
        }
        else if (current_card_number == total_cards) {
            if ($(`${location} #arrow-forward`).hasClass('active')) {
                $(`${location} #arrow-forward`).removeClass('active')
            }
            if (!$(`${location} #arrow-back`).hasClass('active') && total_cards != 1) {
                $(`${location} #arrow-back`).addClass('active')
            }
        }
        else {
            if (!$(`${location} #arrow-forward`).hasClass('active')) {
                $(`${location} #arrow-forward`).addClass('active')
            }
            if (!$(`${location} #arrow-back`).hasClass('active')) {
                $(`${location} #arrow-back`).addClass('active')
            }
        }
    }
}

let current_card_number = 1;
let current_card = get_card_from_table(1);
let total_cards = $('table tr').length;
let current_side = 0;
$('#card').flip({
    trigger: 'click'
}); // Enable the flip library

function card_back() {
    if (current_card_number != 1) {
        current_card_number -= 1;
        current_card = get_card_from_table(current_card_number);
        update_card();
        update_arrows();
        $("#card h2").boxfit({multiline: true, maximum_font_size: 25});
    }
}

function card_forward() {
    if (current_card_number != total_cards) {
        current_card_number += 1;
        current_card = get_card_from_table(current_card_number);
        update_card();
        update_arrows();
        $("#card h2").boxfit({multiline: true, maximum_font_size: 25});
    }
}

function showDialog(dialog_name, transition=true) {
    let initial_duration
    if (dialog_name === 'share' && visibility === 'private') {
        socket.emit("make_public", {"set_id": set_id}, (response) => {
            if (response[0] === 401) {
                $("#share-link-container").html("<p>There was an issue sharing your set. Reload the page and try again.</p>")
            }
            else {
                $("#share-link").val("https://share.hashcards.net/" + response[1]);
            }
        });
    }
    else if (dialog_name === 'share' &&  $("#share-link").val() === "https://hashcards.net" + window.location.pathname) {
        socket.emit("make_shorturl", {"set_id": set_id}, (response) => {
            if (response[0] === 401) {
                $("#share-link-container").html("<p>There was an issue generating the short url. Reload the page and try again.</p>")
            }
            else {
                $("#share-link").val("https://share.hashcards.net/" + response[1]);
            }
        });
    }
    if (!transition) {
        $("#popup-modal").addClass("notransition");
    }
    $("#popup-modal").show();
    $(`#popup #${dialog_name}`).show();
    $("#popup-modal").addClass("active");
    if (!transition) {
        $("#popup-modal").removeClass("notransition");
    }
}

function hideDialog(delay=true) {
    $("#popup-modal").removeClass("active");
    if (delay) {
        setTimeout(function(){
            $("#popup-modal").hide();
            $("#popup-modal #popup > div").hide();
        }, 300)
    }
    else {
        $("#popup-modal").hide();
        $("#popup-modal #popup > div").hide();
    }
}

$(document).ready(function(){
    hideDialog(0);
    $('body').on("keydown", function(e){
        if (e.keyCode === 32) {
            e.preventDefault();
            $('#card').flip('toggle');
        }
        else if (e.keyCode === 37) {
            card_back();
            e.preventDefault();
        }
        else if (e.keyCode === 39) {
            card_forward();
            e.preventDefault();
        }
    });
    $("#pin-set").on("click", function(e) {
        fetch('/api/v1/account/pin', {
                method: 'POST',
                headers: {
                          'Accept': 'application/json',
                          'Content-Type': 'application/json'
                        },
                credentials: 'include',
                body: JSON.stringify({set_id: set_id})
            }).then(r => {
                if (r.status === 401) {
                    window.alert("Could not pin set - you are not signed in.");
                }
                else {
                    if ($("#pin-set").text() == "push_pin Pin") {
                        $("#pin-set").html("<span class=\"material-symbols-outlined\">push_pin</span> Unpin");
                    }
                    else {
                        $("#pin-set").html("<span class=\"material-symbols-outlined\">push_pin</span> Pin");
                    }
                }
            });
    });
})

// --- Convert as required to MathQuill
$(document).ready(function() {
    let to_convert = $(".convertMQ");
    to_convert.each(function (i) {
        MQ.StaticMath(to_convert.get(i));
    })
});
// ---x