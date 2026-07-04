browser.action.onClicked.addListener(async (tab) => {
  if (tab.url) {
    try {
      await fetch("http://localhost:5000", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: tab.url })
      });
      console.log("Lähetetty jonoon: " + tab.url);
    } catch (error) {
      console.error("Ohjelma ei ole päällä?", error);
    }
  }
});