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
    if (go) window.location.href = window.location.href;
}

function tableSort(value) {
  arrow_up = '↑';
  arrow_down = '↓';
  sort_arg = "sort_by_asc";

  if(event.target.innerHTML.includes(arrow_up))  {
    sort_arg = "sort_by_desc";
    setSearchParam("sort_by_asc", null);
  } else{
    setSearchParam("sort_by_desc", null);
  }

  setSearchParam(sort_arg, value);
}

function cancelTableSort(e) {
  $("#sort_param").attr('disabled', 'disabled');
  setSearchParam("sort_by_desc", null, false);
  setSearchParam("sort_by_asc", null);
}

function fakeInputButtonToggle(config = {
  inputGroup: '.input-group-fake',
  button: 'button'
}, callback = () => {}) {
  $(config.inputGroup).find(config.button).on('click', function(e){
    e.preventDefault();
    if($(this).data('action') === 1) {
      callback($(this));
    }
    $(this).parents(config.inputGroup).toggleClass('d-none');
    $(this).parents(config.inputGroup).siblings('.input-group').not('.input-group-fake').toggleClass('d-none');
  });
}
fakeInputButtonToggle();
// callback для вставки данных