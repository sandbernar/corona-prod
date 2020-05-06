var setSearchParam = function(key, value, go = true) {
    if (!window.history.pushState) {
      return;
    }

    if (!key) {
      return;
    }

    var url = new URL(window.location.href);
    var params = new window.URLSearchParams(window.location.search);
    if (value === undefined || value === null) {
      params.delete(key);
    } else {
      params.set(key, value);
    }

    url.search = params;
    url = url.toString();
    window.history.replaceState({url: url}, null, url);
    if (go) window.location.href = window.location.href
}

function tableSort(value) {
  arrow_up = '↑';
  arrow_down = '↓';
  sort_arg = "sort_by_asc"

  if(event.target.innerHTML.includes(arrow_up))  {
    sort_arg = "sort_by_desc"
    setSearchParam("sort_by_asc", null)
  } else{
    setSearchParam("sort_by_desc", null)
  }

  setSearchParam(sort_arg, value)
}