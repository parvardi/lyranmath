import streamlit as st
import bcrypt
import streamlit_authenticator as stauth
from neo4j import GraphDatabase
import random
import subprocess
import tempfile
import os
from PIL import Image

# ---------------------
# Set Streamlit Page Configuration FIRST
st.set_page_config(
    page_title="🧮 LyranMath: AI-Powered Math Education",  # Your desired title
    page_icon="🧮",  # URL or relative path to your favicon
    layout="wide",  # Optional: 'centered' or 'wide'
    initial_sidebar_state="expanded"  # Optional: 'auto', 'expanded', 'collapsed'
)

# ---------------------
# Database Connection 
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
except Exception as e:
    st.error(f"❌ Failed to connect to Neo4j: {e}")

# ---------------------
# Database Functions

def create_user(username, password_hash):
    query = """
    CREATE (u:User {username: $username, password_hash: $password_hash})
    RETURN u
    """
    with driver.session() as session:
        session.run(query, username=username, password_hash=password_hash)

def get_user(username):
    query = """
    MATCH (u:User {username:$username})
    RETURN u.username AS username, u.password_hash AS password_hash
    """
    with driver.session() as session:
        res = session.run(query, username=username).single()
        if res:
            return {
                "username": res["username"],
                "password_hash": res["password_hash"]
            }
    return None

def verify_user_credentials(username, password):
    user = get_user(username)
    if user:
        return bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8'))
    return False

def log_problem_feedback(username, problem_id, feedback_type):
    """
    Logs the user's feedback with a timestamp.
    """
    query = f"""
    MATCH (u:User {{username: $username}})
    MATCH (p:Problem {{problem_id: $pid}})
    CREATE (u)-[r:{feedback_type} {{timestamp: timestamp()}}]->(p)
    RETURN r
    """
    with driver.session() as session:
        session.run(query, username=username, pid=problem_id)

def get_user_history(username):
    """
    Retrieves the user's history ordered by timestamp ascending (oldest first).
    """
    query = """
    MATCH (u:User {username: $username})-[r]->(p:Problem)
    RETURN p.problem_id AS problem_id, TYPE(r) AS feedback_type, r.timestamp AS timestamp
    ORDER BY r.timestamp ASC
    """
    with driver.session() as session:
        results = session.run(query, username=username).data()
        return results

def get_problem_by_category(category):
    query = """
    MATCH (p:Problem)
    WHERE p.type = $category
    WITH p, rand() as r
    ORDER BY r
    LIMIT 1
    RETURN p.problem_id AS problem_id, p.problem AS problem, p.solution AS solution
    """
    with driver.session() as session:
        res = session.run(query, category=category).single()
        if res:
            return {
                "problem_id": res["problem_id"],
                "problem": res["problem"],
                "solution": res["solution"]
            }
    return None

def get_similar_problems(problem_id):
    query = """
    MATCH (p:Problem {problem_id: $pid})-[:SIMILAR_TO]->(other:Problem)
    RETURN other.problem_id AS problem_id, other.problem AS problem, other.solution AS solution
    ORDER BY rand()
    LIMIT 3
    """
    with driver.session() as session:
        results = session.run(query, pid=problem_id).data()
        return results

def get_another_problem_in_category(category, exclude_id):
    query = """
    MATCH (p:Problem)
    WHERE p.type = $category AND p.problem_id <> $exclude_id
    WITH p, rand() as r
    ORDER BY r
    LIMIT 1
    RETURN p.problem_id AS problem_id, p.problem AS problem, p.solution AS solution
    """
    with driver.session() as session:
        res = session.run(query, category=category, exclude_id=exclude_id).single()
        if res:
            return {
                "problem_id": res["problem_id"],
                "problem": res["problem"],
                "solution": res["solution"]
            }
    return None

def get_problem_by_id(pid):
    query = """
    MATCH (p:Problem {problem_id: $pid})
    RETURN p.problem_id AS problem_id, p.problem AS problem, p.solution AS solution
    """
    with driver.session() as session:
        res = session.run(query, pid=pid).single()
        if res:
            return {
                "problem_id": res["problem_id"],
                "problem": res["problem"],
                "solution": res["solution"]
            }
    return None

# ---------------------
# Asymptote Rendering Functions
def render_asy(asy_code: str):
    import subprocess, tempfile, os
    from PIL import Image
    import streamlit as st

    current_dir = os.getcwd()

    with tempfile.NamedTemporaryFile(suffix=".asy", dir=current_dir, delete=False) as tmp:
        tmp.write(asy_code.encode('utf-8'))
        tmp_name = tmp.name

    png_name = tmp_name.replace(".asy", ".png")

    # Run asy with explicit PNG format and output file
    result = subprocess.run(["asy", "-f", "png", "-o", png_name, tmp_name], capture_output=True, text=True)

    if result.returncode != 0:
        st.error("Asymptote error (stderr):\n" + result.stderr)
        st.error("Asymptote output (stdout):\n" + result.stdout)
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise RuntimeError("Asymptote failed to produce output. Check the error messages above.")

    if not os.path.exists(png_name):
        st.error(f"No PNG file was produced by Asymptote. Expected at: {png_name}")
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise RuntimeError("No PNG file produced by Asymptote.")

    img = Image.open(png_name)

    # Clean up
    if os.path.exists(tmp_name):
        os.remove(tmp_name)
    if os.path.exists(png_name):
        os.remove(png_name)

    return img

def process_text_with_asy(text: str):
    # Convert LaTeX delimiters
    text = text.replace("\\[", "$$\\begin{aligned}").replace("\\]", "\\end{aligned}$$\n")
    text = text.replace("\\begin{align*}", "\n$$\\begin{aligned}")
    text = text.replace("\\end{align*}", "\\end{aligned}$$\n")

    # Remove newline characters within LaTeX equations
    text = text.replace("\n\\[", "$$").replace("\\]\n", "$$")
    text = text.replace("\n$$", "$$").replace("$$\n", "$$")

    start_tag = "[asy]"
    end_tag = "[/asy]"
    parts = []
    start_idx = 0
    while True:
        asy_start = text.find(start_tag, start_idx)
        if asy_start == -1:
            parts.append(text[start_idx:])
            break
        asy_end = text.find(end_tag, asy_start)
        if asy_end == -1:
            parts.append(text[start_idx:])
            break

        parts.append(text[start_idx:asy_start])
        asy_code = text[asy_start+len(start_tag):asy_end].strip()
        # Add size commands
        asy_code = asy_code + "unitsize(35mm);\nsize(2000,2000);\n"
        asy_code = "import olympiad;\n" + asy_code

        try:
            img = render_asy(asy_code)
            parts.append(img)
        except RuntimeError:
            parts.append("ASY_RENDER_ERROR")

        start_idx = asy_end + len(end_tag)

    return parts

# ---------------------
# Logout Function

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.category = None
    st.session_state.current_problem = None
    st.success("✅ Logged out successfully!")
    st.rerun()

# ---------------------
# Streamlit UI and State Management

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "category" not in st.session_state:
    st.session_state.category = None
if "current_problem" not in st.session_state:
    st.session_state.current_problem = None

# Authentication section
st.title("LyranMath - AI-Powered Math Education")

if not st.session_state.authenticated:
    st.header("Login or Sign Up")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if verify_user_credentials(login_username, login_password):
                st.session_state.authenticated = True
                st.session_state.username = login_username
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials. Please try again.")

    with signup_tab:
        signup_username = st.text_input("New Username", key="signup_username")
        signup_password = st.text_input("New Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            if get_user(signup_username) is not None:
                st.error("❌ Username already exists. Please choose a different username.")
            else:
                hashed_pw = bcrypt.hashpw(signup_password.encode('utf-8'), bcrypt.gensalt())
                create_user(signup_username, hashed_pw.decode('utf-8'))
                st.success("✅ Account created! Please log in.")
else:
    st.write(f"👋 Hello, **{st.session_state.username}**!")

    # --- Move History to the Sidebar ---
    st.sidebar.subheader("📜 My History")
    # Add CSS to make the history section scrollable if it gets too long
    st.sidebar.markdown("""
    <style>
    /* Limit the height of the sidebar history section and make it scrollable */
    .history-container {
        max-height: 400px;
        overflow-y: auto;
    }
    </style>
    <div class="history-container">
    """, unsafe_allow_html=True)

    history = get_user_history(st.session_state.username)
    if history:
        for idx, h in enumerate(history, 1):
            display_text = f"{idx}. Problem ID: {h['problem_id']} (Feedback: {h['feedback_type']})"
            if st.sidebar.button(display_text, key=f"history_{h['problem_id']}_{idx}"):
                loaded_prob = get_problem_by_id(h['problem_id'])
                if loaded_prob:
                    st.session_state.current_problem = loaded_prob
                    # Reset the checkbox whenever loading a new problem
                    st.session_state.show_solution = False
                    st.rerun()
                else:
                    st.sidebar.error("❌ Problem not found.")
    else:
        st.sidebar.write("No history yet. Start solving problems to see your history here!")


    # Close the history container div
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    st.sidebar.write("---")  # Separator

    # Logout Button in Sidebar
    st.sidebar.button("🔒 Logout", on_click=logout)

    st.write("---")  # Separator

    # Category Selection or Change Category
    if st.session_state.category is None:
        st.subheader("📂 Choose a Category")
        category_choice = st.selectbox(
            "Select the category you're preparing for:",
            ["Algebra", "Geometry", "Number Theory", "Precalculus", "Counting & Probability"]
        )
        if st.button("Confirm Category"):
            st.session_state.category = category_choice
            st.success(f"📁 Category set to **{category_choice}**!")
            st.rerun()
    else:
        # Display the currently selected category
        st.subheader(f"📂 Current Category: **{st.session_state.category}**")
        if st.button("Change Category"):
            st.session_state.category = None  # Reset the category
            st.session_state.current_problem = None  # Clear the current problem
            st.rerun()

    # Fetch a problem if category is selected and no current problem
    if st.session_state.category and st.session_state.current_problem is None:
        prob = get_problem_by_category(st.session_state.category)
        if prob:
            st.session_state.current_problem = prob
            st.rerun()
        else:
            st.error("❌ No problems found for this category.")

    # Fetch a problem if category is selected and no current problem
    if st.session_state.category and st.session_state.current_problem is None:
        prob = get_problem_by_category(st.session_state.category)
        if prob:
            st.session_state.current_problem = prob
            st.rerun()
        else:
            st.error("❌ No problems found for this category.")

    # Display the current problem
    if st.session_state.current_problem:
        st.subheader(f"📝 Problem in {st.session_state.category}")
        st.markdown("**Problem:**")

        problem_content = process_text_with_asy(st.session_state.current_problem["problem"])
        for item in problem_content:
            if isinstance(item, str):
                st.markdown(item)
            else:
                st.image(item, use_container_width=True)

        show_solution = st.checkbox("🔍 Show Solution", key="show_solution")
        if show_solution:
            st.markdown("**Solution:**")
            solution_content = process_text_with_asy(st.session_state.current_problem["solution"])
            for item in solution_content:
                if isinstance(item, str):
                    st.markdown(item)
                else:
                    st.image(item, use_container_width=True)


        st.write("**Did you find this problem useful?**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 Yes, I liked it"):
                log_problem_feedback(st.session_state.username, st.session_state.current_problem["problem_id"], "LIKED")
                similar = get_similar_problems(st.session_state.current_problem["problem_id"])
                if similar:
                    st.session_state.current_problem = random.choice(similar)
                    st.success("✅ Great! Here's a similar problem for you.")
                else:
                    st.warning("⚠️ No similar problems found. Selecting another problem from the same category.")
                    next_prob = get_another_problem_in_category(st.session_state.category, st.session_state.current_problem["problem_id"])
                    if next_prob:
                        st.session_state.current_problem = next_prob
                    else:
                        st.error("❌ No other problems found in this category.")
                st.rerun()

        with col2:
            if st.button("👎 Not really"):
                log_problem_feedback(st.session_state.username, st.session_state.current_problem["problem_id"], "DISLIKED")
                next_prob = get_another_problem_in_category(st.session_state.category, st.session_state.current_problem["problem_id"])
                if next_prob:
                    st.session_state.current_problem = next_prob
                    st.success("🔄 Here's another problem for you.")
                else:
                    st.error("❌ No other problems found in this category.")
                st.rerun()
