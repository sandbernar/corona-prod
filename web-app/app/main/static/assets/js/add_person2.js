var geoCodeMap;
var geoCoder;
var geoCodeResult;

// Функция ymaps.ready() будет вызвана, когда
// загрузятся все компоненты API, а также когда будет готово DOM-дерево.
ymaps.ready(init);
function init(){
	console.log('hey!')
    // Создание карты.
    // var myMap = new ymaps.Map("map", {
    //     // Координаты центра карты.
    //     // Порядок по умолчанию: «широта, долгота».
    //     // Чтобы не определять координаты центра карты вручную,
    //     // воспользуйтесь инструментом Определение координат.
    //     center: [55.76, 37.64],
    //     // Уровень масштабирования. Допустимые значения:
    //     // от 0 (весь мир) до 19.
    //     zoom: 7
    // });


	// geoCoder = ymaps.geocode("Алматы, Таирова 54");
	// geoCoder.then(
	//     function (res) {
	//         // myMap.geoObjects.add(res.geoObjects);

	//         geoCodeResult = res.geoObjects.get(0).properties.get('metaDataProperty');
	//         if (geoCodeResult) {
	//         	console.log(geoCodeResult.GeocoderMetaData.Address.formatted);
	        	
	//         	let result = geoCodeResult.GeocoderMetaData.Address.formatted;

	//         	let resultHtml = "<li><a href=\"#\">"+result+"</a></li>";


	//         	$('#inlineFormInputGroupAddress1').closest('.location-detection-block').find('.location-hints ul').html(resultHtml);
	//         }

	//         console.log('res:')
	//         console.log(res)
	//         // Выведем в консоль данные, полученные в результате геокодирования объекта.
	//         console.log(res.geoObjects.get(0).properties.get('metaDataProperty').getAll());
	//     },
	//     function (err) {
	//     	console.log('ymaps error:')
	//     	console.log(err)
	//         // Обработка ошибки.
	//     }
	// );
}





$(document).ready(function() {
	var locInput1 =  $('#inlineFormInputGroupAddress1');

	locInput1.keyup(function() {
		let value = $(this).val();
		if (value.length > 2) {

			hintLocationsFromText($(this), value);



		}
	})
})

var geoCodeResultObjects;

function hintLocationsFromText(input, value) {
	
	geoCoder = ymaps.geocode(value);


	geoCoder.then(
	    function (res) {
	        // myMap.geoObjects.add(res.geoObjects);

	        geoCodeResult = res;

	        geoCodeResultObjects = res.geoObjects;

	        if (geoCodeResult) {
	        	let r = geoCodeResult.geoObjects.get(0).properties.get('metaDataProperty')

	        	let numberOfResults = geoCodeResult.metaData.geocoder.results;
	        	let found = geoCodeResult.metaData.geocoder.found;
	        	if (found < numberOfResults) {
	        		numberOfResults = found;
	        	}

				let resultsArr = prepareSearchResults(geoCodeResult.geoObjects, numberOfResults);

				drawLocatonHints(input, resultsArr);

				initHintBlockClicks();

	        }

	    },
	    function (err) {
	    	console.log('ymaps error:')
	    	console.log(err)
	        // Обработка ошибки.
	    }
	);
}

function prepareSearchResults(objects, numberOfResults) {

	var resultsArr = [];

	console.log('goind through the loop')

	for (var i = 0; i < numberOfResults; i++) {

		console.log(i);
		resultsArr.push(objects.get(i).properties.get('metaDataProperty').GeocoderMetaData.Address.formatted);

	}

	return resultsArr;

}


function drawLocatonHints(input, results) {

	let resultHtml = "";


	results.forEach(function(result) {

		resultHtml += "<li><a href=\"#\">"+result+"</a></li>";
		
	})

	input.closest('.location-detection-block').find('.location-hints ul').html(resultHtml);
}

function initHintBlockClicks() {
	$('.location-hints a').click(function(e) {
		e.preventDefault();
		
		let block = $(this).closest('.location-detection-block');

		let value = $(this).text();

		block.find('.location-input').val(value);

		block.find('.location-hints').html('')

	})
}