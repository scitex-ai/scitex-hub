// File history functionality

function filterByAuthor(author: string) {
  if (author) {
    window.location.href = "?page=1&author=" + encodeURIComponent(author);
  } else {
    window.location.href = "?page=1";
  }
}
