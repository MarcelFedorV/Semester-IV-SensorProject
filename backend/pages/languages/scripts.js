function setLanguage(selectElement) {
    var selectedValue = "";
    if (typeof selectElement === "string") {
        selectedValue = selectElement.toLowerCase();
    } else {
        selectedValue = String(selectElement.value).toLowerCase();
    }
    console.log("Selected:", selectedValue);
    const langSwitcher = document.getElementById('langSwitcher');
    if (langSwitcher) {
        langSwitcher.value = selectedValue;
    }
//   localStorage.setItem('lang', selectedValue);

  changeLanguage();
}

function changeLanguage() {
    // const lang = localStorage.getItem('lang') || 'en';
    const langSwitcher = document.getElementById('langSwitcher');
    const lang = (langSwitcher && langSwitcher.value) || document.documentElement.lang || 'en';
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
            const entry = translations[el.id];
            if (!entry) {
                return;
            }
            console.log(entry["en"]);
            el.innerHTML = entry[lang] || entry.en || el.innerHTML;
        });

}

function translateText(key) {
    const langSwitcher = document.getElementById('langSwitcher');
    const lang = (langSwitcher && langSwitcher.value) || document.documentElement.lang || 'en';
    const entry = translations[key];
    if (!entry) {
        return '';
    }
    return entry[lang] || entry.en || '';
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
    const langSwitcher = document.getElementById("langSwitcher");
    const language = langSwitcher ? langSwitcher.value : document.documentElement.lang || "en";
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
