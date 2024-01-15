function showNotification(link) {
    // Display the notification
    document.getElementById("successNotification").style.display = "block";

    // Set the link for the notification
    document.getElementById("notificationLink").href = link;
};

function closeNotification() {
    // Close the notification
    document.getElementById("successNotification").style.display = "none";
};


function myFunction() {

    var input, filter, ul, li, la, i, txtValue;
    input = document.getElementById("myInput");
    filter = input.value.toUpperCase();
    ul = document.getElementById("myUL");
    li = ul.getElementsByTagName("li");

    for (i = 0; i < li.length; i++) {
      la = li[i].getElementsByTagName("label")[0];
      txtValue = la.textContent || la.innerText;
      if (txtValue.toUpperCase().indexOf(filter) > -1) {
        li[i].style.display = "";
      } else {
        li[i].style.display = "none";
      }
    }
  };
