import csv


def find_airport(city):
    city = city.capitalize()
    city_length = len(city)
    city_short = city[:city_length-1]
    city_name = ''
    with open('files/distances.csv', 'r', newline='', encoding='utf-8') as file:
        csv_data = csv.DictReader(file, delimiter=';')
        for row in csv_data:
            if row['\ufeffcity'].startswith(city_short):
                min_distance = 0
                for field in csv_data.fieldnames:
                    try:
                        data = int(row[field])
                        if min_distance == 0:
                            min_distance = data
                            city_name = field
                        else:
                            if data < min_distance:
                                min_distance = data
                                city_name = field
                    except ValueError:
                        pass
                return city_name


if __name__ == "__main__":
    name = find_airport('мурманску')
    print(name)
