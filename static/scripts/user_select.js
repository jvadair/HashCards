// noinspection DuplicatedCode

let currently_enabled = [];
let management_buttons_shown = false;
function toggle_user(user_id) {
    // Toggle status
    if (currently_enabled.includes(user_id)) {
        console.log('OK');
        currently_enabled.splice(currently_enabled.indexOf(user_id), 1);  // Why doesn't js just have a .remove method?!
    }
    else {
        currently_enabled.push(user_id);
    }
    // Update buttons, if needed
    if (currently_enabled.length === 0 && management_buttons_shown) {
        $("#management-buttons").hide();
        management_buttons_shown = false;
    }
    else if (!management_buttons_shown) {
        $("#management-buttons").show();
        management_buttons_shown = true;
    }
}