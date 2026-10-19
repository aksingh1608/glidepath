// Shared banner and footer. Numbers on the site come from data/results.json.
(function () {
  const banner = document.getElementById("banner");
  const PILOT = "Pilot study on one evening of data. Replay of test flights the model never saw. Not for operational use.";
  const SYN = "SYNTHETIC TEST DATA. These numbers come from simulated flights, not from Frankfurt. Research demo, not for operational use.";
  if (banner) banner.textContent = PILOT;
  window.glidepathLabel = function (synthetic) {
    if (!banner) return;
    banner.textContent = synthetic ? SYN : PILOT;
    banner.classList.toggle("synthetic", !!synthetic);
  };
  const footer = document.getElementById("footer");
  if (footer) {
    footer.innerHTML =
      '<div>Data: The OpenSky Network. Map: OpenFreeMap, OpenMapTiles, OpenStreetMap contributors.</div>' +
      '<div><a href="terms.html">Terms</a><a href="privacy.html">Privacy</a>' +
      '<a href="https://github.com/aksingh1608/glidepath">GitHub repo</a>' +
      '<a href="https://bewithaksingh.com">bewithaksingh.com</a></div>';
  }
})();
