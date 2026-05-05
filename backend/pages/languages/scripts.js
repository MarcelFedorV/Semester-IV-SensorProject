function setLanguage(selectElement) {
  const selectedValue = selectElement.value.toLowerCase();
  console.log("Selected:", selectedValue);

  localStorage.setItem('lang', selectedValue);

  changeLanguage();
}

function changeLanguage() {
    const lang = localStorage.getItem('lang') || 'en';
    
    // fetch("/languages/translations.js")
    // .then(response => response.json())
    // // .then(data => {
    // //     console.log(data); // this is your list (array)
    // // });


    //change all the text
    const elements = document.querySelectorAll(".languageclass");
        elements.forEach(el => {
            console.log(el.id);
            console.log(translations[el.id]["en"]);
            el.textContent = translations[el.id][lang];
        });

}

// const translations = {
//     "logo-text": {
//         "en": "SensorProject",
//         "dk": "SensorProjekt"
//     },
//     "logo-sub": {
//         "en": "Semester IV · Group 11",
//         "dk": "Semester IV · Gruppe 11"
//     }
// };