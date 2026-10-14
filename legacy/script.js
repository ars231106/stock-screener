// ---------------- Stock Screener Logic (Enhanced) ----------------
document.addEventListener("DOMContentLoaded", function () {
  // ============ CONSTANTS & SELECTORS ============
  const searchBtn = document.getElementById("searchBtn");
  const searchInput = document.getElementById("searchInput");
  const metricsSection = document.getElementById("metricsSection");
  const authModal = document.getElementById("authModal");
  const loginBtn = document.querySelector(".login-btn");
  const signupBtn = document.querySelector(".signup-btn");
  const closeModal = document.querySelector(".close");
  const formTitle = document.getElementById("formTitle");
  const submitAuth = document.getElementById("submitAuth");
  const toggleAuth = document.getElementById("toggleAuth");
  const popularTags = document.querySelectorAll(".tag-list button");
 
  // Real-time stock data API key
  const apiKey = "6RMY30H0S0EZTTA7"; // Keeping your original API key
  let isLoginMode = true;
  let activeStockSymbol = null;
  let refreshInterval = null;


  // ============ INITIALIZATION ============
  initApp();


  function initApp() {
    setupEventListeners();
    checkLoggedInStatus();
    setupPopularTags();
   
    // Add keyboard accessibility
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && authModal.style.display === "block") {
        authModal.style.display = "none";
      }
    });
  }


  // ============ EVENT LISTENERS ============
  function setupEventListeners() {
    // Search functionality
    searchBtn.addEventListener("click", handleSearch);
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSearch();
      }
    });
   
    // Auth modal
    loginBtn.addEventListener("click", () => showModal("login"));
    signupBtn.addEventListener("click", () => showModal("signup"));
    closeModal.addEventListener("click", () => closeAuthModal());
   
    // Auth toggle
    toggleAuth.addEventListener("click", () => {
      isLoginMode = !isLoginMode;
      updateAuthMode();
    });
   
    // Form submission
    submitAuth.addEventListener("click", handleAuthSubmit);


    // Handle window closing to clear intervals
    window.addEventListener("beforeunload", () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    });
  }
 
  function setupPopularTags() {
    popularTags.forEach(tag => {
      tag.addEventListener("click", () => {
        searchInput.value = tag.textContent.trim();
        handleSearch();
      });
    });
  }


  // ============ AUTHENTICATION ============
  function handleAuthSubmit() {
    const username = document.getElementById("authUsername").value.trim();
    const password = document.getElementById("authPassword").value;


    if (!username || !password) {
      alert("Please fill in both fields.");
      return;
    }
   
    if (isLoginMode) {
      loginUser(username, password);
    } else {
      registerUser(username, password);
    }
  }
 
  function loginUser(username, password) {
    const storedPassword = localStorage.getItem(`user_${username}`);
   
    if (storedPassword === password) {
      // Set session expiry (24 hours)
      const session = {
        username: username,
        expires: Date.now() + (24 * 60 * 60 * 1000)
      };
     
      localStorage.setItem("loggedInUser", JSON.stringify(session));
      updateUIForUser(username);
      closeAuthModal();
      alert("Login successful!");
    } else {
      alert("Incorrect username or password.");
    }
  }
 
  function registerUser(username, password) {
    // Check for existing user
    if (localStorage.getItem(`user_${username}`)) {
      alert("User already exists.");
      return;
    }
   
    // Password validation
    if (password.length < 6) {
      alert("Password must be at least 6 characters.");
      return;
    }
   
    localStorage.setItem(`user_${username}`, password);
    alert("Signup successful! You can now login.");
    isLoginMode = true;
    updateAuthMode();
  }
 
  function updateAuthMode() {
    formTitle.textContent = isLoginMode ? "Login" : "Sign Up";
    submitAuth.textContent = isLoginMode ? "Login" : "Register";
    toggleAuth.innerHTML = isLoginMode
      ? `Don't have an account? <span id="switchToSignup">Sign up</span>`
      : `Already have an account? <span id="switchToLogin">Login</span>`;
  }
 
  function checkLoggedInStatus() {
    try {
      const userSession = JSON.parse(localStorage.getItem("loggedInUser") || "null");
     
      if (userSession) {
        // Check if session expired
        if (userSession.expires && userSession.expires < Date.now()) {
          localStorage.removeItem("loggedInUser");
          return;
        }
       
        updateUIForUser(userSession.username);
      }
    } catch (error) {
      console.error("Session error:", error);
      localStorage.removeItem("loggedInUser");
    }
  }
 
  function updateUIForUser(username) {
    const authButtons = document.querySelector(".auth-buttons");
    authButtons.innerHTML = `
      <p class="welcome-user">Hi, ${username}!</p>
      <button id="logoutBtn" class="login-btn">Logout</button>
    `;
   
    document.getElementById("logoutBtn").addEventListener("click", () => {
      localStorage.removeItem("loggedInUser");
      // Clear any active intervals when logging out
      if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
      }
      location.reload();
    });
  }
 
  function showModal(mode) {
    isLoginMode = mode === "login";
    updateAuthMode();
    authModal.style.display = "block";
    document.getElementById("authUsername").focus();
  }
 
  function closeAuthModal() {
    authModal.style.display = "none";
    document.getElementById("authUsername").value = "";
    document.getElementById("authPassword").value = "";
  }


  // ============ STOCK SEARCH & REAL-TIME DATA ============
  function handleSearch() {
    const query = searchInput.value.trim();


    if (!query) {
      alert("Please enter a company name or stock symbol.");
      return;
    }


    try {
      const userSession = JSON.parse(localStorage.getItem("loggedInUser") || "null");
      if (!userSession) {
        alert("Please login to use the stock screener.");
        showModal("login");
        return;
      }
    } catch (error) {
      alert("Session error. Please login again.");
      localStorage.removeItem("loggedInUser");
      showModal("login");
      return;
    }
   
    // Clear any existing refresh interval
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
   
    // Show loading state
    metricsSection.innerHTML = `
      <div class="loading-container">
        <p>Searching for ${query}...</p>
      </div>
    `;


    searchStock(query);
  }
 
  function searchStock(query) {
    fetch(`https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=${encodeURIComponent(query)}&apikey=${apiKey}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}`);
        }
        return response.json();
      })
      .then(searchData => {
        // Handle API limit message
        if (searchData.Note) {
          metricsSection.innerHTML = `<p class="api-limit-message">API limit reached. Please try again in a minute.</p>`;
          return;
        }


        if (!searchData.bestMatches || searchData.bestMatches.length === 0) {
          metricsSection.innerHTML = `<p class="no-results-message">No matching company found for "${query}".</p>`;
          return;
        }


        const bestMatch = searchData.bestMatches[0];
        const symbol = bestMatch["1. symbol"];
       
        // Store active symbol for refresh
        activeStockSymbol = {
          symbol: symbol,
          companyData: bestMatch
        };
       
        fetchStockData(bestMatch, symbol);
       
        // Set up real-time refresh (every 60 seconds)
        // AlphaVantage has rate limits, so don't refresh too frequently
        refreshInterval = setInterval(() => {
          if (activeStockSymbol) {
            fetchStockData(activeStockSymbol.companyData, activeStockSymbol.symbol, true);
          }
        }, 60000); // Refresh every minute
      })
      .catch(error => {
        console.error("Search Error:", error);
        metricsSection.innerHTML = `<p class="error-message">Search failed. Please try again later.</p>`;
      });
  }
 
  function fetchStockData(bestMatch, symbol, isRefresh = false) {
    const region = bestMatch["4. region"];
    const currency = bestMatch["8. currency"];
    const currencySymbol = getCurrencySymbol(currency);
   
    // If refreshing, show a subtle indicator
    if (isRefresh) {
      const metricsCard = document.querySelector(".metrics-card");
      if (metricsCard) {
        const refreshIndicator = document.createElement("div");
        refreshIndicator.className = "refresh-indicator";
        refreshIndicator.textContent = "Refreshing...";
        metricsCard.appendChild(refreshIndicator);
       
        // Remove indicator after 2 seconds
        setTimeout(() => {
          if (refreshIndicator.parentNode) {
            refreshIndicator.parentNode.removeChild(refreshIndicator);
          }
        }, 2000);
      }
    }
   
    fetch(`https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${encodeURIComponent(symbol)}&apikey=${apiKey}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`API request failed with status ${response.status}`);
        }
        return response.json();
      })
      .then(quoteData => {
        // Handle API limit message
        if (quoteData.Note) {
          if (!isRefresh) {
            metricsSection.innerHTML = `<p class="api-limit-message">API limit reached. Please try again in a minute.</p>`;
          }
          return;
        }
       
        const quote = quoteData["Global Quote"];
        if (!quote || !quote["01. symbol"]) {
          if (!isRefresh) {
            metricsSection.innerHTML = `<p class="error-message">Could not fetch stock data for ${symbol}.</p>`;
          }
          return;
        }


        displayStockData(bestMatch, quote, currencySymbol, region);
       
        // Add last updated timestamp
        const lastUpdatedElement = document.getElementById("last-updated");
        if (lastUpdatedElement) {
          const now = new Date();
          lastUpdatedElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        }
      })
      .catch(error => {
        console.error("Quote Fetch Error:", error);
        if (!isRefresh) {
          metricsSection.innerHTML = `<p class="error-message">Something went wrong. Please try again later.</p>`;
        }
      });
  }
 
  function displayStockData(bestMatch, quote, currencySymbol, region) {
    const symbol = quote["01. symbol"];
    const price = parseFloat(quote["05. price"]).toFixed(2);
    const open = parseFloat(quote["02. open"]).toFixed(2);
    const high = parseFloat(quote["03. high"]).toFixed(2);
    const low = parseFloat(quote["04. low"]).toFixed(2);
    const prevClose = parseFloat(quote["08. previous close"]).toFixed(2);
    const volume = Number(quote["06. volume"]).toLocaleString();
    const change = parseFloat(quote["09. change"]).toFixed(2);
    const changePercent = quote["10. change percent"];
   
    const changeClass = parseFloat(change) >= 0 ? "positive-change" : "negative-change";
    const changeSign = parseFloat(change) >= 0 ? "+" : "";
   
    metricsSection.innerHTML = `
      <div class="metrics-card">
        <h2 class="stock-title">${bestMatch["2. name"]} (${symbol}) - ${region}</h2>
        <div class="price-row">
          <p class="current-price">${currencySymbol}${price}</p>
          <p class="${changeClass}">${changeSign}${change} (${changePercent})</p>
        </div>
        <div class="metrics-grid">
          <p><strong>Open:</strong> ${currencySymbol}${open}</p>
          <p><strong>High:</strong> ${currencySymbol}${high}</p>
          <p><strong>Low:</strong> ${currencySymbol}${low}</p>
          <p><strong>Previous Close:</strong> ${currencySymbol}${prevClose}</p>
          <p><strong>Volume:</strong> ${volume}</p>
        </div>
        <div id="last-updated" class="last-updated">
          Last updated: ${new Date().toLocaleTimeString()}
        </div>
        <button id="refresh-btn" class="refresh-btn">
          Refresh Data
        </button>
      </div>
    `;
   
    // Add manual refresh button event listener
    document.getElementById("refresh-btn").addEventListener("click", () => {
      if (activeStockSymbol) {
        fetchStockData(activeStockSymbol.companyData, activeStockSymbol.symbol, true);
      }
    });
  }
 
  // ============ UTILITY FUNCTIONS ============
  function getCurrencySymbol(currency) {
    const currencySymbols = {
      "USD": "$",
      "INR": "₹",
      "EUR": "€",
      "GBP": "£",
      "JPY": "¥"
    };
   
    return currencySymbols[currency] || currency;
  }
});


// FOOTER FUNCTIONALITY
const footerModal = document.getElementById("footer-modal");
const footerModalBody = document.getElementById("footer-modal-body");
const footerModalClose = document.getElementById("footer-modal-close");


document.getElementById("learn-btn").addEventListener("click", () => {
  footerModalBody.innerHTML = `<h2>Learn</h2><p>Explore how to analyze stocks, read financials, and use screener.in for smart investing. Coming soon!</p>`;
  footerModal.style.display = "block";
});


document.getElementById("about-btn").addEventListener("click", () => {
  footerModalBody.innerHTML = `<h2>About Us</h2><p>This platform was built by Aryan Surani to help investors explore Indian and global stocks using a clean, fast UI.</p>`;
  footerModal.style.display = "block";
});


document.getElementById("support-btn").addEventListener("click", () => {
  footerModalBody.innerHTML = `<h2>Support</h2><p>Need help? Contact Aryan at <a href="mailto:aryan@example.com">aryan@example.com</a> or DM on Instagram @aryan_surani.</p>`;
  footerModal.style.display = "block";
});


footerModalClose.addEventListener("click", () => {
  footerModal.style.display = "none";
});


window.addEventListener("click", (event) => {
  if (event.target === footerModal) {
    footerModal.style.display = "none";
  }
});


// THEME TOGGLE
document.getElementById("light-theme").addEventListener("click", () => {
  document.body.classList.remove("dark-theme");
});


document.getElementById("dark-theme").addEventListener("click", () => {
  document.body.classList.add("dark-theme");
});


// ---------------- Theme Management ----------------
document.addEventListener("DOMContentLoaded", function() {
  const lightThemeBtn = document.getElementById("light-theme");
  const darkThemeBtn = document.getElementById("dark-theme");
 
  // Apply the saved theme on page load
  initTheme();
 
  // Set up theme toggle listeners
  lightThemeBtn.addEventListener("click", () => {
    setTheme("light");
  });
 
  darkThemeBtn.addEventListener("click", () => {
    setTheme("dark");
  });
 
  // Theme initialization
  function initTheme() {
    const savedTheme = localStorage.getItem("preferred-theme");
   
    // Apply saved theme or use system preference as default
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Check system preference
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        setTheme("dark");
      } else {
        setTheme("light");
      }
    }
   
    // Listen for system theme changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem("preferred-theme")) {
          setTheme(e.matches ? "dark" : "light");
        }
      });
    }
  }
 
  // Theme application function
  function setTheme(theme) {
    if (theme === "dark") {
      document.body.classList.add("dark-theme");
      updateActiveThemeButton("dark");
    } else {
      document.body.classList.remove("dark-theme");
      updateActiveThemeButton("light");
    }
   
    // Save preference to localStorage
    localStorage.setItem("preferred-theme", theme);
  }
 
  // Update visual indicator of active theme
  function updateActiveThemeButton(activeTheme) {
    // Remove active class from both buttons
    lightThemeBtn.classList.remove("active-theme");
    darkThemeBtn.classList.remove("active-theme");
   
    // Add active class to the selected theme button
    if (activeTheme === "dark") {
      darkThemeBtn.classList.add("active-theme");
    } else {
      lightThemeBtn.classList.add("active-theme");
    }
  }
});


// ---------------- Navigation Tabs Logic ----------------
document.addEventListener("DOMContentLoaded", function() {
  // ============ NAVIGATION CONSTANTS & SELECTORS ============
  const navLinks = document.querySelectorAll("nav ul li a");
  const homeLink = document.querySelector("nav ul li:nth-child(1) a");
  const screensLink = document.querySelector("nav ul li:nth-child(2) a");
  const toolsLink = document.querySelector("nav ul li:nth-child(3) a");
 
  // Main content areas
  const heroSection = document.querySelector(".hero");
  const metricsSection = document.getElementById("metricsSection");
 
  // Initialize content containers for different views
  let screensSection, toolsSection;
 
  // Track current active view
  let currentView = "home";
 
  // ============ INITIALIZATION ============
  initNavigation();
 
  function initNavigation() {
    createContentSections();
    setupNavEventListeners();
   
    // Set home as default active tab
    setActiveTab(homeLink);
    showView("home");
  }
 
  // ============ CREATE SECTION ELEMENTS ============
  function createContentSections() {
    // Create Screens section
    screensSection = document.createElement("section");
    screensSection.id = "screensSection";
    screensSection.className = "content-section";
    screensSection.style.display = "none";
    screensSection.innerHTML = `
      <div class="content-container">
        <h2>Stock Screeners</h2>
        <p>Discover stocks based on specific criteria and parameters.</p>
       
        <div class="screener-grid">
          <div class="screener-card">
            <h3>Growth Stocks</h3>
            <p>Stocks with above-average revenue and earnings growth</p>
            <ul>
              <li>Revenue Growth > 15%</li>
              <li>EPS Growth > 15%</li>
              <li>ROE > 15%</li>
            </ul>
            <button class="view-stocks-btn">View Stocks</button>
          </div>
         
          <div class="screener-card">
            <h3>Value Stocks</h3>
            <p>Stocks trading below their intrinsic value</p>
            <ul>
              <li>P/E < 15</li>
              <li>P/B < 1.5</li>
              <li>Dividend Yield > 2%</li>
            </ul>
            <button class="view-stocks-btn">View Stocks</button>
          </div>
         
          <div class="screener-card">
            <h3>Dividend Stocks</h3>
            <p>Stocks with consistent dividend payments</p>
            <ul>
              <li>Dividend Yield > 3%</li>
              <li>Payout Ratio < 70%</li>
              <li>5yr Dividend Growth > 0</li>
            </ul>
            <button class="view-stocks-btn">View Stocks</button>
          </div>
         
          <div class="screener-card">
            <h3>Create Custom Screen</h3>
            <p>Build your own stock screen with custom parameters</p>
            <button class="custom-screen-btn">Create Screen</button>
          </div>
        </div>
      </div>
    `;
   
    // Create Tools section
    toolsSection = document.createElement("section");
    toolsSection.id = "toolsSection";
    toolsSection.className = "content-section";
    toolsSection.style.display = "none";
    toolsSection.innerHTML = `
      <div class="content-container">
        <h2>Investment Tools</h2>
        <p>Helpful tools for stock analysis and investment decisions.</p>
       
        <div class="tools-grid">
          <div class="tool-card">
            <h3>Portfolio Tracker</h3>
            <p>Track your investment portfolio performance over time</p>
            <button class="tool-btn">Open Tool</button>
          </div>
         
          <div class="tool-card">
            <h3>Stock Comparison</h3>
            <p>Compare multiple stocks side by side</p>
            <button class="tool-btn">Open Tool</button>
          </div>
         
          <div class="tool-card">
            <h3>Return Calculator</h3>
            <p>Calculate potential returns on your investments</p>
            <button class="tool-btn">Open Tool</button>
          </div>
         
          <div class="tool-card">
            <h3>Technical Analysis</h3>
            <p>Chart patterns and technical indicators</p>
            <button class="tool-btn">Open Tool</button>
          </div>
        </div>
      </div>
    `;
   
    // Add sections to the document
    metricsSection.parentNode.insertBefore(screensSection, metricsSection);
    metricsSection.parentNode.insertBefore(toolsSection, metricsSection);
   
    // Add event listeners to the screens and tools buttons
    addSectionEventListeners();
  }
 
  function addSectionEventListeners() {
    // Add event listeners for screener cards
    if (screensSection) {
      const viewStocksButtons = screensSection.querySelectorAll('.view-stocks-btn');
      viewStocksButtons.forEach(button => {
        button.addEventListener('click', function() {
          const screenName = this.parentNode.querySelector('h3').textContent;
          alert(`Loading ${screenName} screen... This feature will be available soon.`);
        });
      });
     
      const customScreenBtn = screensSection.querySelector('.custom-screen-btn');
      if (customScreenBtn) {
        customScreenBtn.addEventListener('click', function() {
          alert("Custom screen builder will be available soon!");
        });
      }
    }
   
    // Add event listeners for tool cards
    if (toolsSection) {
      const toolButtons = toolsSection.querySelectorAll('.tool-btn');
      toolButtons.forEach(button => {
        button.addEventListener('click', function() {
          const toolName = this.parentNode.querySelector('h3').textContent;
          alert(`Opening ${toolName}... This feature will be available soon.`);
        });
      });
    }
  }
 
  // ============ NAVIGATION EVENT LISTENERS ============
  function setupNavEventListeners() {
    navLinks.forEach(link => {
      link.addEventListener("click", function(e) {
        e.preventDefault();
       
        // First remove active class from all links
        navLinks.forEach(l => l.classList.remove("active-nav"));
       
        // Add active class to clicked link
        this.classList.add("active-nav");
       
        // Determine which view to show
        const linkText = this.textContent.toLowerCase();
        showView(linkText);
      });
    });
  }
 
  // ============ VIEW MANAGEMENT ============
  function showView(view) {
    // Save current view
    currentView = view;
   
    // Hide all sections first
    heroSection.style.display = "none";
    metricsSection.style.display = "none";
    screensSection.style.display = "none";
    toolsSection.style.display = "none";
   
    // Show appropriate section based on view
    switch(view) {
      case "home":
        heroSection.style.display = "block";
        metricsSection.style.display = "block";
        setActiveTab(homeLink);
        break;
      case "screens":
        screensSection.style.display = "block";
        setActiveTab(screensLink);
        break;
      case "tools":
        toolsSection.style.display = "block";
        setActiveTab(toolsLink);
        break;
      default:
        heroSection.style.display = "block";
        metricsSection.style.display = "block";
        setActiveTab(homeLink);
    }
  }
 
  function setActiveTab(activeLink) {
    // Remove active class from all links
    navLinks.forEach(link => link.classList.remove("active-nav"));
   
    // Add active class to selected link
    if (activeLink) {
      activeLink.classList.add("active-nav");
    }
  }
 
  // Expose showView to global scope for use in other scripts
  window.showView = showView;
});



