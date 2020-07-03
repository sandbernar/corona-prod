# Form Progress Bar jQuery plugin
![alt text](https://api.wokay.me/uploads/1528147646.gif)

-Plugin adding progress bar on top to the page, which show how much fields you fill which are required. 

-Modules works with validation libraries

# Live Demo
You can preview this plugin on: https://wokay.me/projects/progressBar/

# Quick Start

Import needed files

```
<script
  src="https://code.jquery.com/jquery-3.3.1.min.js"
  integrity="sha256-FgpCb/KJQlLNfOu91ta32o/NMZxltwRo8QtmkMRdAu8="
  crossorigin="anonymous"></script>
  
  /* plugin files */
<link rel="stylesheet" href="formProgressBar.css">
<script src="formProgressBar.jquery.min.js"></script>
```

Init form

```
$("form").formProgressBar()
```

# Options
`readCount`:true|**false** - If you turn on this option, form will be use classes to count correct fields. If you use Validator libraries, choice this option.

`validClass`:'string' - It's class used by validator to show that field is correct filled. If you enabled readCount progress will be based on valicClass. Default class is **"valid"**

`invalidClass`:'string' - This same rule, if field become invalid, progress bar change color. Class **"error"** is default.

`percentCounting`: true|**false** - If you want show in percent how much fields from required are filled correct you can enable this option

`height`: 'int' in pixel - Set height in pixel of progress bar

`transitionTime`: 'int' in milliseconds - If you want add animation to move progress bar and changing color, set transitionTime to some number in miliseconds

`transitionType`: `ease`|`linear`|`ease-in`|`ease-out`|`ease-in-out` if you set `transitionTime` you can set how transition should looks like

`parentElement`: 'string' default: **body** Element where progressbar html is located

**Example initializate option**
```
$("form").formProgressBar({
        readCount: false,
        validClass: 'valid',
        invalidClass: 'error',
        percentCounting: false,
        height: 20,
        transitionTime: 0,
        transitionType: 'ease' //
});
```

# How color change works
There are 2 classes
`warn` and `error` which are added to `#jQueryProgressFormBar > div`
if some field is invalid to progress bar is added class `warn`
if you have class `warn` and you try submit form, class is changing for `error`.

In case you want change color of fields use `#jQueryProgressFormBar > div.warn` and `#jQueryProgressFormBar > div.error` selector and change background

# Author

### Krzysztof Łokaj "Wokay"
- Blog https://wokay.me/
- Twitter https://twitter.com/_Wokay
- Linkedin https://www.linkedin.com/in/wokay/
