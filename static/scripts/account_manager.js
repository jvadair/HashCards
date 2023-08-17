$(document).ready(function () {
    $('#user-privacy-delete').on("click", function (event) {
        let response = prompt('Please retype this phrase: "I want to delete my account."');
        if (response === "I want to delete my account.") {
            fetch('/api/v1/account', {
                method: 'DELETE',
                credentials: 'include'
            }).then(r => {
                if (r.status !== 401) {
                    window.location.href = '/';
                }
                else {
                    window.alert("Could not delete account - you are not signed in.")
                }
            });
        }
        else {
            window.alert("Could not delete account: security phrase typed incorrectly")
        }
    });
})