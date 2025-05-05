import streamlit as st
import time
import openai
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adpreview import AdPreview

# === LOAD SECRETS ===
ACCESS_TOKEN = 'EAAPLfuMFEEcBO55HO7ZBMEG5MGBXrxZCe3DeOZCvY6bkffULoe0NzYRl4Q6YoKl6rZA6ZAwfZB8u6q2Npgbu3Te64CogaRzIQ90wt1RunyVJ8rJ7oIC9T70gzMN5EQ2PnpI1hsEa1Ut9YJJjODNBqAPuGSXSKEeHCTfpGZAF25uqy0VDL2kPOWWZCc4YxY7N'
APP_ID = '2528472164160851'
openai.api_key = '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'
ASSISTANT_ID = 'asst_ljKQ5ChpJOfNCrc6Qsw6hj6F'

# === INITIALIZE APIs ===
FacebookAdsApi.init(access_token='EAAPLfuMFEEcBO55HO7ZBMEG5MGBXrxZCe3DeOZCvY6bkffULoe0NzYRl4Q6YoKl6rZA6ZAwfZB8u6q2Npgbu3Te64CogaRzIQ90wt1RunyVJ8rJ7oIC9T70gzMN5EQ2PnpI1hsEa1Ut9YJJjODNBqAPuGSXSKEeHCTfpGZAF25uqy0VDL2kPOWWZCc4YxY7N')

# === UTILITY FUNCTIONS ===
def get_all_ads_from_recent_campaigns(account):
    ad_account = AdAccount(account['id'])
    campaigns = ad_account.get_campaigns(fields=['name', 'id', 'status'])

    ads_data = []

    for campaign in campaigns:
        camp_id = campaign['id']
        camp_name = campaign['name']

        try:
            adsets = Campaign(camp_id).get_ad_sets(fields=['id', 'status'])
            for adset in adsets:
                if adset['status'] != 'ACTIVE':
                    continue
                ads = AdSet(adset['id']).get_ads(fields=['id', 'name', 'status'])
                for ad in ads:
                    insights = Ad(ad['id']).get_insights(params={
                        'date_preset': 'last_7d',
                        'fields': 'spend'
                    })
                    if insights and float(insights[0].get('spend', 0)) > 0:
                        ads_data.append({
                            'ad_id': ad['id'],
                            'ad_name': ad['name'],
                            'campaign_name': camp_name
                        })
        except Exception as e:
            st.warning(f"⚠️ Error fetching ad sets or ads for campaign {camp_name}: {e}")
            continue

    return ads_data

def get_ad_preview_html(ad_id):
    try:
        preview = Ad(ad_id).get_previews(params={'ad_format': 'DESKTOP_FEED_STANDARD'})
        return preview[0]['body'] if preview else None
    except Exception as e:
        st.error(f"❌ Preview error for Ad ID {ad_id}: {e}")
        return None

def analyze_with_agent(ad_name, preview_html):
    try:
        thread = openai.beta.threads.create()

        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Ad Name: {ad_name}\nPreview HTML: {preview_html}"
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        with st.spinner(f"Analyzing {ad_name}..."):
            while True:
                run_status = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run_status.status == "completed":
                    break
                time.sleep(1)

        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text.value

        st.markdown(f"### 🧠 Analysis for: {ad_name}")
        st.markdown(response_text)
        st.divider()
    except Exception as e:
        st.error(f"❌ AI analysis error for '{ad_name}': {e}")

# === STREAMLIT INTERFACE ===
st.set_page_config(layout="wide")
st.title("📊 Facebook Ad Intelligence Agent")

me = User(fbid='me')
accounts = me.get_ad_accounts(fields=['name', 'id'])

# Build a dropdown menu from your accounts
account_options = {f"{acct['name']} ({acct['id']})": acct for acct in accounts}
selected_label = st.selectbox("Select an Ad Account to Analyze:", list(account_options.keys()))
selected_account = account_options[selected_label]

st.subheader(f"🔍 Analyzing Account: {selected_account['name']} ({selected_account['id']})")
ads = get_all_ads_from_recent_campaigns(selected_account)

if not ads:
    st.write("❌ No qualifying ads found in the last 7 days.")
else:
    for ad in ads:
        preview_html = get_ad_preview_html(ad['ad_id'])
        if preview_html:
            analyze_with_agent(ad_name=ad['ad_name'], preview_html=preview_html)
            time.sleep(10)  # ⏱️ Add delay to avoid hitting API limits
        else:
            st.warning(f"⚠️ Skipping preview for {ad['ad_name']}")
