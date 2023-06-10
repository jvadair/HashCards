var socket = io.connect(location.protocol + "//" + document.domain + ':' + location.port);
$(document).ready(function() {
  $("#card-container").sortable({
      axis: "y",
      containment: "#card-container",
      cursor: "grabbing",
      handle: ".drag-handle",
      update: function(event, ui) {
      // Get the updated order of the flashcards
      const cardOrder = $(this)
        .find(".flashcard")
        .map(function() {
          return $(this).data("card-id");
        })
        .get();

      // Send the updated order to the server via Socket.IO
      socket.emit("flashcardOrderChanged", cardOrder);
    }
  });
});
