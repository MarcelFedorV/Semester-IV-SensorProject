function setLanguage(selectElement) {
    var selectedValue = "";
    if (typeof selectElement === "string") {
        selectedValue = selectElement.toLowerCase();
    } else {
        selectedValue = String(selectElement.value).toLowerCase();
    }
    console.log("Selected:", selectedValue);
    document.getElementById('langSwitcher').value = selectedValue;
//   localStorage.setItem('lang', selectedValue);

  changeLanguage();
}

function changeLanguage() {
    // const lang = localStorage.getItem('lang') || 'en';
    const lang = document.getElementById('langSwitcher').value || 'en';
    // document.getElementById('langSwitcher').value = lang;
    
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
            el.innerHTML = translations[el.id][lang];
        });

}

async function loadLanguage() {
    try {
        const response = await fetch('/api/user');
        const data = await response.json();
        
        if (response.ok) {
            console.log("User data:", data);
            const lang = data.language.toString() || 'en';
            console.log("User language:", lang);
            setLanguage(lang);
        } else {
            console.log('Failed to load user data');
        }
    } catch (error) {
        console.log('Error loading language');
        console.error(error);
    }
}

async function saveLanguage() {
    const language = document.getElementById("langSwitcher").value;
    console.log("Saving language:", language);

    try {
        const response = await fetch('/api/user', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                language: language || "en",
            })
        });

        if (response.ok) {
            console.log('Language updated successfully');
        } else {
            console.log('Failed to update language');
        }
    } catch (error) {
        console.log('Error saving language');
        console.error(error);
    }
}
