# === IMPORTS ===
import streamlit as st
import time
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adpreview import AdPreview
import openai

# === SECRETS (replace with Streamlit secrets later) ===
ACCESS_TOKEN = 'EAAPLfuMFEEcBO55HO7ZBMEG5MGBXrxZCe3DeOZCvY6bkffULoe0NzYRl4Q6YoKl6rZA6ZAwfZB8u6q2Npgbu3Te64CogaRzIQ90wt1RunyVJ8rJ7oIC9T70gzMN5EQ2PnpI1hsEa1Ut9YJJjODNBqAPuGSXSKEeHCTfpGZAF25uqy0VDL2kPOWWZCc4YxY7N'
APP_ID = '2528472164160851'
openai.api_key = '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'
ASSISTANT_ID = 'asst_ljKQ5ChpJOfNCrc6Qsw6hj6F'

# === INIT APIS ===
FacebookAdsApi.init(access_token='EAAPLfuMFEEcBO55HO7ZBMEG5MGBXrxZCe3DeOZCvY6bkffULoe0NzYRl4Q6YoKl6rZA6ZAwfZB8u6q2Npgbu3Te64CogaRzIQ90wt1RunyVJ8rJ7oIC9T70gzMN5EQ2PnpI1hsEa1Ut9YJJjODNBqAPuGSXSKEeHCTfpGZAF25uqy0VDL2kPOWWZCc4YxY7N')

# === FUNCTIONS ===
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
                ads = AdSet(adset['id']).get_ads(fields=['id', 'name', 'status'])
                for ad in ads:
                    insights = Ad(ad['id']).get_insights(params={
                        'date_preset': 'last_7d',
                        'fields': 'spend'
                    })
                    spend = float(insights[0].get('spend', 0)) if insights else 0
                    if spend > 0 or ad['status'] == 'ACTIVE':
                        ads_data.append({
                            'ad_id': ad['id'],
                            'ad_name': ad['name'],
                            'campaign_name': camp_name
                        })
        except Exception as e:
            st.warning(f"⚠️ Error fetching ads in {camp_name}: {e}")
            continue

    return ads_data

def get_ad_preview_html(ad_id):
    try:
        preview = Ad(ad_id).get_previews(params={'ad_format': 'DESKTOP_FEED_STANDARD'})
        return preview[0]['body'] if preview else None
    except Exception as e:
        st.error(f"❌ Error loading preview for Ad ID {ad_id}: {e}")
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
            assistant_id=AGENT_ID
        )

        with st.spinner(f"Analyzing '{ad_name}'..."):
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

# === UI ===
st.set_page_config(layout="wide")
st.title("📊 Facebook Ad Intelligence Agent")

try:
    me = User(fbid='me')
    accounts = me.get_ad_accounts(fields=['name', 'id'])

    for account in accounts:
        st.subheader(f"🔍 Account: {account['name']} ({account['id']})")
        ads = get_all_ads_from_recent_campaigns(account)

        if not ads:
            st.write("No ads spent money in the past 7 days.")
            continue

        for ad in ads:
            preview_html = get_ad_preview_html(ad['ad_id'])
            if preview_html:
                analyze_with_agent(ad_name=ad['ad_name'], preview_html=preview_html)
            else:
                st.warning(f"⚠️ Skipping preview for {ad['ad_name']}")
except Exception as e:
    st.error(f"🚨 App Error: {e}")
