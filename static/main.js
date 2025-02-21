// Global variables to store daily nutrition data
let dailyNutrition = {
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0
};

// Food database (simplified version - in production, this would come from an API)
const foodDatabase = {
    'apple': { calories: 95, protein: 0.5, carbs: 25, fat: 0.3 },
    'banana': { calories: 105, protein: 1.3, carbs: 27, fat: 0.4 },
    'chicken breast': { calories: 165, protein: 31, carbs: 0, fat: 3.6 },
    'rice': { calories: 130, protein: 2.7, carbs: 28, fat: 0.3 }
};

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize food search
    const foodForm = document.getElementById('food-form');
    const foodSearch = document.getElementById('food-search');
    const foodResults = document.getElementById('food-results');

    foodForm.addEventListener('submit', function(e) {
        e.preventDefault();
        searchFood(foodSearch.value);
    });

    // Username change handler
    const usernameInput = document.getElementById('username');
    usernameInput.addEventListener('change', function() {
        localStorage.setItem('username', this.value);
    });

    // Load saved username
    const savedUsername = localStorage.getItem('username');
    if (savedUsername) {
        usernameInput.value = savedUsername;
    }

    // Load initial data
    loadDailySummary();
    loadMealPlan();
    loadRecipeSuggestions();
});

// Food search function
function searchFood(query) {
    const results = Object.entries(foodDatabase)
        .filter(([name]) => name.includes(query.toLowerCase()))
        .map(([name, nutrition]) => ({name, ...nutrition}));
    
    displayFoodResults(results);
}

// Display food search results
function displayFoodResults(results) {
    const foodResults = document.getElementById('food-results');
    foodResults.innerHTML = '';

    results.forEach(food => {
        const foodItem = document.createElement('div');
        foodItem.className = 'food-item';
        foodItem.innerHTML = `
            <div class="d-flex justify-content-between">
                <strong>${food.name}</strong>
                <span>${food.calories} cal</span>
            </div>
            <div class="small text-muted">
                P: ${food.protein}g | C: ${food.carbs}g | F: ${food.fat}g
            </div>
            <button class="btn btn-sm btn-primary mt-2" onclick="addFoodToLog('${food.name}')">
                Add to Log
            </button>
        `;
        foodResults.appendChild(foodItem);
    });
}

// Add food to daily log
function addFoodToLog(foodName) {
    const food = foodDatabase[foodName.toLowerCase()];
    if (!food) return;

    // Update daily nutrition
    dailyNutrition.calories += food.calories;
    dailyNutrition.protein += food.protein;
    dailyNutrition.carbs += food.carbs;
    dailyNutrition.fat += food.fat;

    // Update UI
    updateNutritionDisplay();
    
    // Save to backend
    saveFoodLog(foodName, food);
}

// Update nutrition display
function updateNutritionDisplay() {
    document.getElementById('total-calories').textContent = Math.round(dailyNutrition.calories);
    document.getElementById('total-protein').textContent = Math.round(dailyNutrition.protein);
    document.getElementById('total-carbs').textContent = Math.round(dailyNutrition.carbs);
    document.getElementById('total-fat').textContent = Math.round(dailyNutrition.fat);

    // Update progress bar
    const progressBar = document.querySelector('.progress-bar');
    const percentage = (dailyNutrition.calories / 2000) * 100;
    progressBar.style.width = `${Math.min(percentage, 100)}%`;
}

// Save food log to backend
async function saveFoodLog(foodName, nutrition) {
    try {
        const response = await fetch('/api/log-food', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                food_name: foodName,
                calories: nutrition.calories
            })
        });
        const data = await response.json();
        if (data.status !== 'success') {
            console.error('Failed to save food log');
        }
    } catch (error) {
        console.error('Error saving food log:', error);
    }
}

// Load daily summary from backend
async function loadDailySummary() {
    try {
        const response = await fetch('/api/get-logs');
        const logs = await response.json();
        
        // Reset daily nutrition
        dailyNutrition = {
            calories: 0,
            protein: 0,
            carbs: 0,
            fat: 0
        };

        // Calculate totals
        logs.forEach(log => {
            const food = foodDatabase[log.food_name.toLowerCase()];
            if (food) {
                dailyNutrition.calories += food.calories;
                dailyNutrition.protein += food.protein;
                dailyNutrition.carbs += food.carbs;
                dailyNutrition.fat += food.fat;
            }
        });

        updateNutritionDisplay();
    } catch (error) {
        console.error('Error loading daily summary:', error);
    }
}

// Load meal plan
function loadMealPlan() {
    // This would typically load from backend
    // For now, we'll just show placeholder content
    const meals = ['breakfast', 'lunch', 'dinner', 'snacks'];
    meals.forEach(meal => {
        const container = document.getElementById(`${meal}-items`);
        container.innerHTML = '<p class="text-muted">Drop food items here</p>';
    });
}

// Load recipe suggestions
function loadRecipeSuggestions() {
    const suggestions = [
        { name: 'Healthy Smoothie Bowl', calories: 350 },
        { name: 'Grilled Chicken Salad', calories: 400 },
        { name: 'Quinoa Buddha Bowl', calories: 450 }
    ];

    const container = document.getElementById('recipe-suggestions');
    container.innerHTML = suggestions.map(recipe => `
        <div class="col-md-4">
            <div class="card recipe-card">
                <div class="card-body">
                    <h6>${recipe.name}</h6>
                    <p class="text-muted">${recipe.calories} calories</p>
                </div>
            </div>
        </div>
    `).join('');
}
