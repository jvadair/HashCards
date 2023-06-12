function get_card_from_table(n) {
    let row = $(`table tr:nth-of-type(${n})`);
    let front = $(`table tr:nth-of-type(${n}) td:nth-of-type(2)`).text();
    let back = $(`table tr:nth-of-type(${n}) td:nth-of-type(3)`).text();
    return [front, back];
}

function update_card() {
    $('#card').replaceWith("<div id='card'></div>")  // Replacing the card is the only way to avoid the animation
    $('#card').append(`<div class='front'><h2>${current_card[0]}</h2></div>`)
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
        }
        else if (current_card_number == total_cards) {
            if ($(`${location} #arrow-forward`).hasClass('active')) {
                $(`${location} #arrow-forward`).removeClass('active')
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
    }
}

function card_forward() {
    if (current_card_number != total_cards) {
        current_card_number += 1;
        current_card = get_card_from_table(current_card_number);
        update_card()
        update_arrows();
    }
}