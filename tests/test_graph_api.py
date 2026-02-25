from shared.services.graph_api import GraphAPI, HARYANA_DISTRICTS, DISTRICTS_PER_PAGE


def test_district_pagination():
      total = len(HARYANA_DISTRICTS)
      total_pages = (total + DISTRICTS_PER_PAGE - 1) // DISTRICTS_PER_PAGE

      # Page 0 — first 8 districts + "Agla" button
      page0 = HARYANA_DISTRICTS[0:8]
      assert len(page0) == 8
      assert page0[0] == "Ambala"
      assert page0[7] == "Jhajjar"
      print(f"Page 0: {page0} + Agla button")

      # Page 1 — next 8 districts + "Pichla" + "Agla"
      page1 = HARYANA_DISTRICTS[8:16]
      assert len(page1) == 8
      assert page1[0] == "Jind"
      print(f"Page 1: {page1} + Pichla + Agla buttons")

      # Page 2 — remaining districts + "Pichla" (no "Agla" — last page)
      page2 = HARYANA_DISTRICTS[16:24]
      assert len(page2) == 6
      assert page2[-1] == "Yamunanagar"
      print(f"Page 2: {page2} + Pichla button")

      assert total_pages == 3
      print(f"Total districts: {total}, Pages: {total_pages}")
      print("District pagination OK")


def test_graph_api_init():
      api = GraphAPI(access_token="test_token", graph_api_url="https://example.com")
      assert api.access_token == "test_token"
      assert api.base_url == "https://example.com"
      assert "Bearer test_token" in api.headers["Authorization"]
      print("GraphAPI init OK")


if __name__ == "__main__":
      test_district_pagination()
      test_graph_api_init()
      print("Graph API OK")
